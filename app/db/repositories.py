"""Repository pattern: typed query helpers for each aggregate root.

Each repository wraps a SQLAlchemy ``Session`` and exposes intention-revealing
methods. Service-layer code never writes raw SQL or calls ``session.query``
directly; it asks a repository.
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime, timezone

from sqlalchemy import desc, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.models import Conversation, Message, MessageRole, User, UserRole
from app.exceptions import NotFoundError, UserAlreadyExistsError


# ---------------------------------------------------------------------------
# Users
# ---------------------------------------------------------------------------
class UserRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def create(
        self,
        username: str,
        email: str,
        hashed_password: str,
        role: UserRole = UserRole.USER,
    ) -> User:
        user = User(
            username=username,
            email=email,
            hashed_password=hashed_password,
            role=role,
        )
        self.session.add(user)
        try:
            self.session.flush()
        except IntegrityError as exc:
            self.session.rollback()
            raise UserAlreadyExistsError(
                f"User with username={username!r} or email={email!r} already exists",
                cause=exc,
            ) from exc
        return user

    def get(self, user_id: str) -> User | None:
        return self.session.get(User, user_id)

    def get_or_raise(self, user_id: str) -> User:
        user = self.get(user_id)
        if user is None:
            raise NotFoundError(f"User {user_id!r} not found")
        return user

    def get_by_username(self, username: str) -> User | None:
        stmt = select(User).where(User.username == username)
        return self.session.execute(stmt).scalar_one_or_none()

    def get_by_email(self, email: str) -> User | None:
        stmt = select(User).where(User.email == email)
        return self.session.execute(stmt).scalar_one_or_none()

    def list_all(self) -> Sequence[User]:
        stmt = select(User).order_by(User.created_at.desc())
        return self.session.execute(stmt).scalars().all()

    def count(self) -> int:
        return int(self.session.execute(select(func.count()).select_from(User)).scalar_one())

    def set_active(self, user_id: str, *, is_active: bool) -> None:
        user = self.get_or_raise(user_id)
        user.is_active = is_active

    def record_login(self, user_id: str) -> None:
        user = self.get_or_raise(user_id)
        user.last_login_at = datetime.now(timezone.utc)


# ---------------------------------------------------------------------------
# Conversations
# ---------------------------------------------------------------------------
class ConversationRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def create(
        self,
        user_id: str,
        *,
        persona: str,
        title: str = "New conversation",
        mood: str = "Happy",
        language: str = "Bangla",
    ) -> Conversation:
        conv = Conversation(
            user_id=user_id,
            title=title,
            mood=mood,
            language=language,
            persona=persona,
        )
        self.session.add(conv)
        self.session.flush()
        return conv

    def get(self, conversation_id: str) -> Conversation | None:
        return self.session.get(Conversation, conversation_id)

    def get_for_user(self, conversation_id: str, user_id: str) -> Conversation | None:
        stmt = select(Conversation).where(
            Conversation.id == conversation_id,
            Conversation.user_id == user_id,
        )
        return self.session.execute(stmt).scalar_one_or_none()

    def list_for_user(self, user_id: str, limit: int = 100) -> Sequence[Conversation]:
        stmt = (
            select(Conversation)
            .where(Conversation.user_id == user_id)
            .order_by(desc(Conversation.updated_at))
            .limit(limit)
        )
        return self.session.execute(stmt).scalars().all()

    def delete(self, conversation_id: str, user_id: str) -> bool:
        conv = self.get_for_user(conversation_id, user_id)
        if conv is None:
            return False
        self.session.delete(conv)
        return True

    def rename(self, conversation_id: str, user_id: str, new_title: str) -> Conversation:
        conv = self.get_for_user(conversation_id, user_id)
        if conv is None:
            raise NotFoundError(f"Conversation {conversation_id!r} not found")
        conv.title = new_title[:200]
        return conv

    def touch(self, conversation_id: str) -> None:
        """Bump updated_at to push conversation to top of list."""
        conv = self.get(conversation_id)
        if conv is not None:
            conv.updated_at = datetime.now(timezone.utc)


# ---------------------------------------------------------------------------
# Messages
# ---------------------------------------------------------------------------
class MessageRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def add(self, conversation_id: str, role: MessageRole, content: str) -> Message:
        msg = Message(conversation_id=conversation_id, role=role, content=content)
        self.session.add(msg)
        self.session.flush()
        return msg

    def list_for_conversation(
        self,
        conversation_id: str,
        limit: int | None = None,
    ) -> Sequence[Message]:
        stmt = (
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(Message.created_at.asc())
        )
        if limit is not None:
            stmt = stmt.limit(limit)
        return self.session.execute(stmt).scalars().all()

    def count_user_messages_since(self, user_id: str, since: datetime) -> int:
        """Count user-role messages a given user has sent since ``since``.

        Used by the rate limiter for persistent across-restart enforcement.
        """
        stmt = (
            select(func.count(Message.id))
            .join(Conversation, Conversation.id == Message.conversation_id)
            .where(
                Conversation.user_id == user_id,
                Message.role == MessageRole.USER,
                Message.created_at >= since,
            )
        )
        return int(self.session.execute(stmt).scalar_one())


__all__ = [
    "ConversationRepository",
    "MessageRepository",
    "UserRepository",
]
