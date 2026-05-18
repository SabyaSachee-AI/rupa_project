"""Retrieval-augmented generation (Pinecone + embeddings).

Two responsibilities:
1. **Ingest** uploaded PDF/DOCX docs into the vector index.
2. **Search** the index for context relevant to a user query.

Embeddings use OpenAI's API directly when ``OPENAI_API_KEY`` is set,
falling back to OpenRouter otherwise. This fixes the production reliability
issue where OpenRouter cannot always proxy OpenAI embedding endpoints.
"""

from __future__ import annotations

import io
import time
from dataclasses import dataclass
from typing import Any, BinaryIO, Protocol

from docx import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from openai import OpenAI
from pinecone import Pinecone
from pypdf import PdfReader
from tenacity import retry, stop_after_attempt, wait_exponential

from app.config import get_settings
from app.exceptions import (
    DocumentParsingError,
    RAGConfigurationError,
    RAGError,
)
from app.logging_setup import get_logger
from app.runtime_keys import (
    get_openai_api_key,
    get_openrouter_api_key,
    get_pinecone_api_key,
    get_pinecone_index_name,
)

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Result types
# ---------------------------------------------------------------------------
@dataclass(frozen=True, slots=True)
class IngestResult:
    files_processed: int
    chunks_uploaded: int
    total_vectors_in_index: int


@dataclass(frozen=True, slots=True)
class SearchHit:
    text: str
    score: float


# ---------------------------------------------------------------------------
# Upload file protocol (Streamlit's UploadedFile is duck-compatible)
# ---------------------------------------------------------------------------
class UploadedFile(Protocol):
    name: str

    def read(self) -> bytes: ...


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------
class RAGService:
    """Vector-DB-backed knowledge base."""

    def __init__(self) -> None:
        settings = get_settings()

        pc_key = get_pinecone_api_key()
        if not pc_key:
            raise RAGConfigurationError(
                "Pinecone API key is not configured. Add it in the sidebar under API keys."
            )

        self._pinecone = Pinecone(api_key=pc_key)
        self._index_name = get_pinecone_index_name()
        self._chunk_size = settings.rag.chunk_size
        self._chunk_overlap = settings.rag.chunk_overlap
        self._top_k = settings.rag.top_k
        self._batch_size = settings.rag.upsert_batch_size

        self._embedding_client = self._build_embedding_client()
        self._embedding_model = settings.llm.embedding_model

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def ingest(self, files: list[UploadedFile]) -> IngestResult:
        """Extract, chunk, embed, and upsert documents."""

        if not files:
            return IngestResult(files_processed=0, chunks_uploaded=0, total_vectors_in_index=0)

        text = self._extract_text(files)
        if not text.strip():
            logger.info("rag.ingest_no_text")
            return IngestResult(
                files_processed=len(files),
                chunks_uploaded=0,
                total_vectors_in_index=self._index_total_vectors(),
            )

        chunks = self._chunk(text)
        logger.info("rag.ingest_start", files=len(files), chunks=len(chunks))

        index = self._pinecone.Index(self._index_name)
        uploaded = 0
        buffer: list[dict[str, Any]] = []
        timestamp = int(time.time())

        for i, chunk in enumerate(chunks):
            embedding = self._embed(chunk)
            buffer.append(
                {
                    "id": f"doc_{timestamp}_{i}",
                    "values": embedding,
                    "metadata": {"text": chunk},
                }
            )
            if len(buffer) >= self._batch_size:
                index.upsert(vectors=buffer)
                uploaded += len(buffer)
                buffer.clear()

        if buffer:
            index.upsert(vectors=buffer)
            uploaded += len(buffer)

        time.sleep(1)
        total = self._index_total_vectors()
        logger.info("rag.ingest_done", uploaded=uploaded, total_in_index=total)
        return IngestResult(
            files_processed=len(files),
            chunks_uploaded=uploaded,
            total_vectors_in_index=total,
        )

    def search(self, query: str) -> list[SearchHit]:
        """Return top-k matches for ``query``. Empty list on any error."""

        if not query or not query.strip():
            return []

        try:
            embedding = self._embed(query)
            index = self._pinecone.Index(self._index_name)
            response = index.query(vector=embedding, top_k=self._top_k, include_metadata=True)
            matches = (
                response.get("matches", []) if isinstance(response, dict) else response.matches
            )
            hits = [
                SearchHit(
                    text=str(m["metadata"].get("text", ""))
                    if isinstance(m, dict)
                    else str(m.metadata.get("text", "")),
                    score=float(m["score"]) if isinstance(m, dict) else float(m.score),
                )
                for m in matches
            ]
            logger.debug("rag.search", query_chars=len(query), hits=len(hits))
            return hits
        except Exception as exc:
            logger.warning("rag.search_failed", error=str(exc))
            return []

    def context_for(self, query: str) -> str:
        """Convenience: search and concatenate hit texts into a single block."""

        return "\n\n".join(h.text for h in self.search(query))

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------
    def _build_embedding_client(self) -> OpenAI:
        settings = get_settings()
        openai_key = get_openai_api_key()
        if openai_key:
            return OpenAI(api_key=openai_key, base_url=settings.llm.openai_base_url)
        logger.warning(
            "rag.embedding_fallback",
            message="OpenAI key not set; falling back to OpenRouter for embeddings "
            "(may be unreliable).",
        )
        or_key = get_openrouter_api_key()
        if not or_key:
            raise RAGConfigurationError(
                "Add an OpenAI key (recommended) or OpenRouter key in the sidebar API keys panel."
            )
        return OpenAI(api_key=or_key, base_url=settings.llm.openrouter_base_url)

    @retry(reraise=True, stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=8))
    def _embed(self, text: str) -> list[float]:
        response = self._embedding_client.embeddings.create(input=text, model=self._embedding_model)
        return list(response.data[0].embedding)

    def _chunk(self, text: str) -> list[str]:
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=self._chunk_size,
            chunk_overlap=self._chunk_overlap,
        )
        chunks: list[str] = splitter.split_text(text)
        return chunks

    def _extract_text(self, files: list[UploadedFile]) -> str:
        out: list[str] = []
        for f in files:
            try:
                name = f.name.lower()
                data: BinaryIO = io.BytesIO(f.read())
                if name.endswith(".pdf"):
                    out.append(self._extract_pdf(data))
                elif name.endswith(".docx"):
                    out.append(self._extract_docx(data))
                else:
                    raise DocumentParsingError(f"Unsupported file type: {f.name}")
            except DocumentParsingError:
                raise
            except Exception as exc:
                raise DocumentParsingError(f"Failed to parse {f.name}: {exc}", cause=exc) from exc
        return "\n".join(out)

    @staticmethod
    def _extract_pdf(data: BinaryIO) -> str:
        reader = PdfReader(data)
        return "\n".join(filter(None, (p.extract_text() for p in reader.pages)))

    @staticmethod
    def _extract_docx(data: BinaryIO) -> str:
        doc = Document(data)
        return "\n".join(p.text for p in doc.paragraphs)

    def _index_total_vectors(self) -> int:
        try:
            index = self._pinecone.Index(self._index_name)
            stats = index.describe_index_stats()
            if isinstance(stats, dict):
                return int(stats.get("total_vector_count", 0))
            return int(getattr(stats, "total_vector_count", 0))
        except Exception as exc:
            logger.warning("rag.stats_failed", error=str(exc))
            raise RAGError("Could not query index stats", cause=exc) from exc


__all__ = ["IngestResult", "RAGService", "SearchHit", "UploadedFile"]
