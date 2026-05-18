"""Persistence layer (SQLAlchemy + Alembic).

Public surface:
- :func:`init_db`           - create schema if it does not exist (dev/SQLite)
- :func:`get_session`       - context manager yielding a transactional Session
- :class:`User`             - account
- :class:`Conversation`     - chat session belonging to a user
- :class:`Message`          - one message within a conversation
- repositories.*            - query helpers
"""

from __future__ import annotations

from app.db.models import Base, Conversation, Message, MessageRole, User, UserRole
from app.db.session import get_engine, get_session, init_db

__all__ = [
    "Base",
    "Conversation",
    "Message",
    "MessageRole",
    "User",
    "UserRole",
    "get_engine",
    "get_session",
    "init_db",
]
