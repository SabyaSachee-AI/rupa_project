"""Tests for the RAG service (Pinecone + embeddings mocked)."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

import pytest

from app.exceptions import RAGConfigurationError
from app.services.rag import RAGService


def _mock_embedding_response(dim: int = 8) -> Any:
    resp = MagicMock()
    resp.data = [MagicMock(embedding=[0.1] * dim)]
    return resp


@pytest.fixture()
def rag_service(mocker: Any) -> RAGService:
    mock_pinecone = MagicMock()
    mock_openai = MagicMock()
    mock_openai.embeddings.create.return_value = _mock_embedding_response()
    mocker.patch("app.services.rag.Pinecone", return_value=mock_pinecone)
    mocker.patch("app.services.rag.OpenAI", return_value=mock_openai)

    service = RAGService()
    service._pinecone = mock_pinecone  # type: ignore[attr-defined]
    service._embedding_client = mock_openai  # type: ignore[attr-defined]
    return service


class _FakeFile:
    def __init__(self, name: str, content: bytes) -> None:
        self.name = name
        self._content = content

    def read(self) -> bytes:
        return self._content


@pytest.mark.unit
class TestRAGServiceConfiguration:
    def test_missing_pinecone_key_raises(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("PINECONE_API_KEY", "")
        from app.config import get_settings

        get_settings.cache_clear()
        with pytest.raises(RAGConfigurationError):
            RAGService()


@pytest.mark.unit
class TestRAGSearch:
    def test_empty_query_returns_empty(self, rag_service: RAGService) -> None:
        assert rag_service.search("") == []
        assert rag_service.search("   ") == []

    def test_search_returns_hits(self, rag_service: RAGService) -> None:
        mock_index = MagicMock()
        rag_service._pinecone.Index.return_value = mock_index  # type: ignore[attr-defined]
        mock_index.query.return_value = {
            "matches": [
                {"metadata": {"text": "hit one"}, "score": 0.91},
                {"metadata": {"text": "hit two"}, "score": 0.83},
            ]
        }

        hits = rag_service.search("what is rupa")
        assert len(hits) == 2
        assert hits[0].text == "hit one"
        assert hits[0].score == pytest.approx(0.91)

    def test_context_for_concatenates(self, rag_service: RAGService) -> None:
        mock_index = MagicMock()
        rag_service._pinecone.Index.return_value = mock_index  # type: ignore[attr-defined]
        mock_index.query.return_value = {
            "matches": [
                {"metadata": {"text": "alpha"}, "score": 0.9},
                {"metadata": {"text": "beta"}, "score": 0.8},
            ]
        }
        assert rag_service.context_for("query") == "alpha\n\nbeta"

    def test_search_failure_returns_empty_list(self, rag_service: RAGService) -> None:
        rag_service._pinecone.Index.side_effect = RuntimeError("pinecone down")  # type: ignore[attr-defined]
        assert rag_service.search("query") == []


@pytest.mark.unit
class TestRAGIngest:
    def test_no_files_returns_zero(self, rag_service: RAGService) -> None:
        result = rag_service.ingest([])
        assert result.files_processed == 0
        assert result.chunks_uploaded == 0

    def test_docx_text_extraction(self, rag_service: RAGService, mocker: Any) -> None:
        fake_doc = MagicMock()
        fake_doc.paragraphs = [MagicMock(text="hello"), MagicMock(text="world")]
        mocker.patch("app.services.rag.Document", return_value=fake_doc)

        mock_index = MagicMock()
        mock_index.describe_index_stats.return_value = {"total_vector_count": 2}
        rag_service._pinecone.Index.return_value = mock_index  # type: ignore[attr-defined]

        result = rag_service.ingest([_FakeFile("doc.docx", b"fake")])
        assert result.files_processed == 1
        assert result.chunks_uploaded >= 1
        assert mock_index.upsert.called

    def test_unsupported_file_raises(self, rag_service: RAGService) -> None:
        from app.exceptions import DocumentParsingError

        with pytest.raises(DocumentParsingError):
            rag_service.ingest([_FakeFile("doc.txt", b"hi")])
