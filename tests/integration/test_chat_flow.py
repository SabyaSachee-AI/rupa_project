"""End-to-end chat-turn integration test with all externals mocked."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

import pytest

from app.auth import AuthenticatedUser
from app.db import get_session
from app.db.models import MessageRole
from app.db.repositories import ConversationRepository, MessageRepository
from app.exceptions import RateLimitError, ValidationError
from app.services.chat import ChatService
from app.services.llm import LLMService
from app.utils.rate_limit import RateLimiter


@pytest.fixture()
def chat_service(mocker: Any) -> ChatService:
    mock_llm = MagicMock(spec=LLMService)
    mock_llm.stream_chat.return_value = iter(["Hello", " ", "world", "."])

    rate_limiter = RateLimiter(messages=100, window_seconds=60)
    return ChatService(llm=mock_llm, rag=None, rate_limiter=rate_limiter)


@pytest.fixture()
def conversation_for_user(regular_user: AuthenticatedUser) -> str:
    with get_session() as session:
        conv = ConversationRepository(session).create(
            regular_user.id,
            persona="You are Rupa.",
        )
        return conv.id


@pytest.mark.integration
class TestChatFlow:
    def test_full_turn_persists_both_messages(
        self,
        chat_service: ChatService,
        regular_user: AuthenticatedUser,
        conversation_for_user: str,
    ) -> None:
        deltas = list(
            chat_service.stream_turn(
                user_id=regular_user.id,
                conversation_id=conversation_for_user,
                user_message="hi",
            )
        )
        assert "".join(deltas) == "Hello world."

        with get_session() as session:
            msgs = list(MessageRepository(session).list_for_conversation(conversation_for_user))
        assert len(msgs) == 2
        assert msgs[0].role is MessageRole.USER
        assert msgs[0].content == "hi"
        assert msgs[1].role is MessageRole.ASSISTANT
        assert msgs[1].content == "Hello world."

    def test_empty_message_rejected(
        self,
        chat_service: ChatService,
        regular_user: AuthenticatedUser,
        conversation_for_user: str,
    ) -> None:
        with pytest.raises(ValidationError):
            list(
                chat_service.stream_turn(
                    user_id=regular_user.id,
                    conversation_id=conversation_for_user,
                    user_message="   ",
                )
            )

    def test_too_long_message_rejected(
        self,
        chat_service: ChatService,
        regular_user: AuthenticatedUser,
        conversation_for_user: str,
    ) -> None:
        with pytest.raises(ValidationError):
            list(
                chat_service.stream_turn(
                    user_id=regular_user.id,
                    conversation_id=conversation_for_user,
                    user_message="x" * 10_000,
                )
            )

    def test_first_user_message_sets_title(
        self,
        chat_service: ChatService,
        regular_user: AuthenticatedUser,
        conversation_for_user: str,
    ) -> None:
        list(
            chat_service.stream_turn(
                user_id=regular_user.id,
                conversation_id=conversation_for_user,
                user_message="What is Rupa AI?",
            )
        )
        with get_session() as session:
            conv = ConversationRepository(session).get(conversation_for_user)
        assert conv is not None
        assert "Rupa" in conv.title

    def test_rate_limit_blocks_excess_traffic(
        self, regular_user: AuthenticatedUser, mocker: Any
    ) -> None:
        mock_llm = MagicMock(spec=LLMService)
        mock_llm.stream_chat.return_value = iter(["ok"])
        limiter = RateLimiter(messages=1, window_seconds=60)
        svc = ChatService(llm=mock_llm, rag=None, rate_limiter=limiter)

        with get_session() as session:
            conv = ConversationRepository(session).create(regular_user.id, persona="x")
            conv_id = conv.id

        list(
            svc.stream_turn(
                user_id=regular_user.id,
                conversation_id=conv_id,
                user_message="first",
            )
        )

        with pytest.raises(RateLimitError):
            list(
                svc.stream_turn(
                    user_id=regular_user.id,
                    conversation_id=conv_id,
                    user_message="second",
                )
            )

    def test_other_user_cannot_post_to_conversation(
        self,
        chat_service: ChatService,
        admin_user: AuthenticatedUser,
        regular_user: AuthenticatedUser,
    ) -> None:
        from app.exceptions import NotFoundError

        with get_session() as session:
            conv = ConversationRepository(session).create(regular_user.id, persona="x")
            conv_id = conv.id

        with pytest.raises(NotFoundError):
            list(
                chat_service.stream_turn(
                    user_id=admin_user.id,
                    conversation_id=conv_id,
                    user_message="hi",
                )
            )
