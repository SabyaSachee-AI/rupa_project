"""Tests for the persistent sliding-window rate limiter."""

from __future__ import annotations

import pytest

from app.auth import AuthenticatedUser
from app.db import get_session
from app.db.models import MessageRole
from app.db.repositories import ConversationRepository, MessageRepository
from app.exceptions import RateLimitError
from app.utils.rate_limit import RateLimiter


def _send_user_messages(user_id: str, count: int) -> None:
    with get_session() as session:
        conv = ConversationRepository(session).create(user_id, persona="x")
        mrepo = MessageRepository(session)
        for _ in range(count):
            mrepo.add(conv.id, MessageRole.USER, "ping")


@pytest.mark.unit
class TestRateLimiter:
    def test_below_limit_passes(self, regular_user: AuthenticatedUser) -> None:
        rl = RateLimiter(messages=10, window_seconds=60)
        _send_user_messages(regular_user.id, 5)
        rl.check(regular_user.id)

    def test_at_limit_raises(self, regular_user: AuthenticatedUser) -> None:
        rl = RateLimiter(messages=3, window_seconds=60)
        _send_user_messages(regular_user.id, 3)
        with pytest.raises(RateLimitError) as exc_info:
            rl.check(regular_user.id)
        assert exc_info.value.retry_after_seconds == 60

    def test_remaining_decreases(self, regular_user: AuthenticatedUser) -> None:
        rl = RateLimiter(messages=10, window_seconds=60)
        assert rl.remaining(regular_user.id) == 10
        _send_user_messages(regular_user.id, 4)
        assert rl.remaining(regular_user.id) == 6

    def test_remaining_clamped_at_zero(self, regular_user: AuthenticatedUser) -> None:
        rl = RateLimiter(messages=3, window_seconds=60)
        _send_user_messages(regular_user.id, 10)
        assert rl.remaining(regular_user.id) == 0

    def test_assistant_messages_not_counted(self, regular_user: AuthenticatedUser) -> None:
        rl = RateLimiter(messages=2, window_seconds=60)
        with get_session() as session:
            conv = ConversationRepository(session).create(regular_user.id, persona="x")
            mrepo = MessageRepository(session)
            for _ in range(5):
                mrepo.add(conv.id, MessageRole.ASSISTANT, "pong")
        rl.check(regular_user.id)
