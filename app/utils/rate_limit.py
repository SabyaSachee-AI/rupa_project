"""Per-user sliding-window rate limiter.

Uses the persistent message store (counts user-role messages in the rolling
window) so limits survive app restarts. For higher-traffic deployments swap
this for Redis with a Lua script; the public interface is small.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from app.config import get_settings
from app.db import get_session
from app.db.repositories import MessageRepository
from app.exceptions import RateLimitError
from app.logging_setup import get_logger

logger = get_logger(__name__)


class RateLimiter:
    """Persistent sliding-window rate limiter."""

    def __init__(self, *, messages: int | None = None, window_seconds: int | None = None) -> None:
        settings = get_settings()
        self.messages = messages if messages is not None else settings.rate_limit.messages
        self.window = timedelta(
            seconds=window_seconds
            if window_seconds is not None
            else settings.rate_limit.window_seconds
        )

    def check(self, user_id: str) -> None:
        """Raise :class:`RateLimitError` if ``user_id`` has exceeded the limit."""

        since = datetime.now(timezone.utc) - self.window
        with get_session() as session:
            count = MessageRepository(session).count_user_messages_since(user_id, since)

        if count >= self.messages:
            retry_after = int(self.window.total_seconds())
            logger.warning(
                "rate_limit.exceeded",
                user_id=user_id,
                count=count,
                limit=self.messages,
                window_seconds=retry_after,
            )
            raise RateLimitError(
                f"User {user_id!r} sent {count} messages in last {self.window}",
                retry_after_seconds=retry_after,
            )

    def remaining(self, user_id: str) -> int:
        """Return how many messages this user can still send in the current window."""

        since = datetime.now(timezone.utc) - self.window
        with get_session() as session:
            count = MessageRepository(session).count_user_messages_since(user_id, since)
        return max(0, self.messages - count)
