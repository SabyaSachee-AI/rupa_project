"""Chat orchestration service.

Coordinates the full request lifecycle for one user turn:

    rate_limit -> persist_user_message -> rag.context_for ->
    build_system_prompt -> llm.stream_chat -> persist_assistant_message

Returns the streaming iterator so the UI can render token-by-token without
the orchestration logic leaking into Streamlit.
"""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass

from app.db import get_session
from app.db.models import Conversation, MessageRole
from app.db.repositories import ConversationRepository, MessageRepository
from app.exceptions import NotFoundError, ValidationError
from app.logging_setup import get_logger
from app.services.llm import ChatMessage, LLMService
from app.services.rag import RAGService
from app.utils.rate_limit import RateLimiter
from app.utils.text import derive_conversation_title

logger = get_logger(__name__)


MAX_USER_MESSAGE_CHARS = 4000
MAX_HISTORY_MESSAGES = 30


@dataclass(frozen=True, slots=True)
class StreamedTurn:
    """Result of streaming one chat turn."""

    conversation_id: str
    user_message_id: str
    assistant_message_id: str
    full_text: str


class ChatService:
    """High-level chat orchestrator."""

    def __init__(
        self,
        llm: LLMService,
        rag: RAGService | None,
        rate_limiter: RateLimiter | None = None,
    ) -> None:
        self._llm = llm
        self._rag = rag
        self._rate_limiter = rate_limiter or RateLimiter()

    # ------------------------------------------------------------------
    # Streaming chat turn
    # ------------------------------------------------------------------
    def stream_turn(
        self,
        *,
        user_id: str,
        conversation_id: str,
        user_message: str,
    ) -> Iterator[str]:
        """Stream one assistant response, persisting both messages.

        The first yield is always at least one token (or empty string on
        empty model output). Callers should accumulate the deltas and
        finally call :meth:`finalise_turn` is **not** required - this method
        already persists both sides.
        """

        user_message = self._validate(user_message)
        self._rate_limiter.check(user_id)

        with get_session() as session:
            conv_repo = ConversationRepository(session)
            msg_repo = MessageRepository(session)

            conv = conv_repo.get_for_user(conversation_id, user_id)
            if conv is None:
                raise NotFoundError(f"Conversation {conversation_id!r} not found")

            user_msg = msg_repo.add(conv.id, MessageRole.USER, user_message)
            if len(conv.messages) <= 1:
                conv.title = derive_conversation_title(user_message)
            history_payload = self._history_payload(conv, msg_repo)
            persona = conv.persona
            mood = conv.mood
            language = conv.language
            user_msg_id = user_msg.id

        context = self._rag_context(user_message)
        system_prompt = self._build_system_prompt(
            persona=persona, mood=mood, language=language, context=context
        )

        messages: list[ChatMessage] = [{"role": "system", "content": system_prompt}]
        messages.extend(history_payload)

        full_text_parts: list[str] = []
        try:
            for delta in self._llm.stream_chat(messages):
                full_text_parts.append(delta)
                yield delta
        finally:
            full_text = "".join(full_text_parts)
            if full_text:
                with get_session() as session:
                    msg_repo = MessageRepository(session)
                    conv_repo = ConversationRepository(session)
                    assistant_msg = msg_repo.add(conversation_id, MessageRole.ASSISTANT, full_text)
                    conv_repo.touch(conversation_id)
                    logger.info(
                        "chat.turn_completed",
                        user_id=user_id,
                        conversation_id=conversation_id,
                        user_message_id=user_msg_id,
                        assistant_message_id=assistant_msg.id,
                        response_chars=len(full_text),
                    )

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------
    @staticmethod
    def _validate(text: str) -> str:
        text = (text or "").strip()
        if not text:
            raise ValidationError("Message cannot be empty")
        if len(text) > MAX_USER_MESSAGE_CHARS:
            raise ValidationError(
                f"Message too long ({len(text)} chars, max {MAX_USER_MESSAGE_CHARS})"
            )
        return text

    # ------------------------------------------------------------------
    # Prompt construction
    # ------------------------------------------------------------------
    @staticmethod
    def _build_system_prompt(*, persona: str, mood: str, language: str, context: str) -> str:
        if language == "English":
            language_rule = "You must reply ONLY in English. Use a natural English voice tone."
        else:
            language_rule = "তোমাকে অবশ্যই শুধুমাত্র বাংলা ভাষায় উত্তর দিতে হবে। কোনো ইংরেজি শব্দ ব্যবহার করো না।"
        mood_rule = (
            "Talk in a very happy and loving way."
            if mood == "Happy"
            else "Talk in a very sad and emotional tone."
        )

        ctx_block = f"\n\nRelevant context from knowledge base:\n{context}" if context else ""

        return (
            f"{persona}\n"
            f"Rule: {language_rule}\n"
            f"Mood: {mood_rule}\n"
            f"Respond concisely (max 2 sentences).{ctx_block}"
        )

    # ------------------------------------------------------------------
    # History payload (trimmed)
    # ------------------------------------------------------------------
    @staticmethod
    def _history_payload(
        conversation: Conversation, msg_repo: MessageRepository
    ) -> list[ChatMessage]:
        all_msgs = msg_repo.list_for_conversation(conversation.id)
        trimmed = list(all_msgs[-MAX_HISTORY_MESSAGES:])
        return [{"role": m.role.value, "content": m.content} for m in trimmed]

    # ------------------------------------------------------------------
    # RAG context (best-effort, never raises)
    # ------------------------------------------------------------------
    def _rag_context(self, query: str) -> str:
        if self._rag is None:
            return ""
        try:
            return self._rag.context_for(query)
        except Exception as exc:
            logger.warning("chat.rag_skipped", error=str(exc))
            return ""


__all__ = ["ChatService", "StreamedTurn"]
