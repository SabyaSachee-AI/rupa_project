"""Tests for the SQLAlchemy repositories."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from app.auth import AuthenticatedUser
from app.db import get_session
from app.db.models import MessageRole
from app.db.repositories import (
    ConversationRepository,
    MessageRepository,
    UserRepository,
)
from app.exceptions import NotFoundError, UserAlreadyExistsError


@pytest.mark.unit
class TestUserRepository:
    def test_create_and_get(self, db_initialised: None) -> None:
        with get_session() as session:
            repo = UserRepository(session)
            user = repo.create("u1", "u1@example.com", "hash")
            fetched = repo.get(user.id)
        assert fetched is not None
        assert fetched.username == "u1"

    def test_duplicate_username_raises(self, db_initialised: None) -> None:
        with get_session() as session:
            repo = UserRepository(session)
            repo.create("u1", "u1@example.com", "h")
            with pytest.raises(UserAlreadyExistsError):
                repo.create("u1", "u2@example.com", "h")

    def test_get_by_username(self, db_initialised: None) -> None:
        with get_session() as session:
            repo = UserRepository(session)
            repo.create("findme", "x@example.com", "h")

        with get_session() as session:
            repo = UserRepository(session)
            assert repo.get_by_username("findme") is not None
            assert repo.get_by_username("missing") is None

    def test_count(self, db_initialised: None) -> None:
        with get_session() as session:
            assert UserRepository(session).count() == 0
            UserRepository(session).create("u1", "u1@example.com", "h")

        with get_session() as session:
            assert UserRepository(session).count() == 1

    def test_get_or_raise(self, db_initialised: None) -> None:
        with get_session() as session, pytest.raises(NotFoundError):
            UserRepository(session).get_or_raise("nonexistent-id")

    def test_record_login_sets_timestamp(self, db_initialised: None) -> None:
        with get_session() as session:
            repo = UserRepository(session)
            user = repo.create("u1", "u1@example.com", "h")
            assert user.last_login_at is None
            user_id = user.id

        with get_session() as session:
            UserRepository(session).record_login(user_id)

        with get_session() as session:
            user = UserRepository(session).get_or_raise(user_id)
        assert user.last_login_at is not None


@pytest.mark.unit
class TestConversationRepository:
    def test_create_lists_for_user(self, regular_user: AuthenticatedUser) -> None:
        with get_session() as session:
            repo = ConversationRepository(session)
            conv = repo.create(regular_user.id, persona="You are Rupa.")
            conv_id = conv.id

        with get_session() as session:
            convs = list(ConversationRepository(session).list_for_user(regular_user.id))
        assert len(convs) == 1
        assert convs[0].id == conv_id

    def test_other_user_cannot_see(
        self, regular_user: AuthenticatedUser, admin_user: AuthenticatedUser
    ) -> None:
        with get_session() as session:
            ConversationRepository(session).create(regular_user.id, persona="x")

        with get_session() as session:
            assert list(ConversationRepository(session).list_for_user(admin_user.id)) == []

    def test_rename(self, regular_user: AuthenticatedUser) -> None:
        with get_session() as session:
            conv = ConversationRepository(session).create(regular_user.id, persona="x")
            conv_id = conv.id

        with get_session() as session:
            ConversationRepository(session).rename(conv_id, regular_user.id, "New title")

        with get_session() as session:
            renamed = ConversationRepository(session).get(conv_id)
        assert renamed is not None
        assert renamed.title == "New title"

    def test_delete(self, regular_user: AuthenticatedUser) -> None:
        with get_session() as session:
            conv = ConversationRepository(session).create(regular_user.id, persona="x")
            conv_id = conv.id

        with get_session() as session:
            assert ConversationRepository(session).delete(conv_id, regular_user.id) is True

        with get_session() as session:
            assert ConversationRepository(session).get(conv_id) is None

    def test_delete_other_user_no_op(
        self, regular_user: AuthenticatedUser, admin_user: AuthenticatedUser
    ) -> None:
        with get_session() as session:
            conv = ConversationRepository(session).create(regular_user.id, persona="x")
            conv_id = conv.id

        with get_session() as session:
            assert ConversationRepository(session).delete(conv_id, admin_user.id) is False


@pytest.mark.unit
class TestMessageRepository:
    def test_add_and_list(self, regular_user: AuthenticatedUser) -> None:
        with get_session() as session:
            conv = ConversationRepository(session).create(regular_user.id, persona="x")
            conv_id = conv.id

        with get_session() as session:
            mrepo = MessageRepository(session)
            mrepo.add(conv_id, MessageRole.USER, "hi")
            mrepo.add(conv_id, MessageRole.ASSISTANT, "hello")

        with get_session() as session:
            msgs = list(MessageRepository(session).list_for_conversation(conv_id))
        assert len(msgs) == 2
        assert msgs[0].role is MessageRole.USER
        assert msgs[1].role is MessageRole.ASSISTANT

    def test_count_user_messages_since(self, regular_user: AuthenticatedUser) -> None:
        with get_session() as session:
            conv = ConversationRepository(session).create(regular_user.id, persona="x")
            mrepo = MessageRepository(session)
            for _ in range(5):
                mrepo.add(conv.id, MessageRole.USER, "ping")
            mrepo.add(conv.id, MessageRole.ASSISTANT, "pong")

        since = datetime.now(timezone.utc) - timedelta(minutes=1)
        with get_session() as session:
            count = MessageRepository(session).count_user_messages_since(regular_user.id, since)
        assert count == 5

    def test_count_zero_in_distant_past(self, regular_user: AuthenticatedUser) -> None:
        future = datetime.now(timezone.utc) + timedelta(minutes=1)
        with get_session() as session:
            count = MessageRepository(session).count_user_messages_since(regular_user.id, future)
        assert count == 0

    def test_cascade_delete_messages_when_conversation_removed(
        self, regular_user: AuthenticatedUser
    ) -> None:
        with get_session() as session:
            conv = ConversationRepository(session).create(regular_user.id, persona="x")
            MessageRepository(session).add(conv.id, MessageRole.USER, "hi")
            conv_id = conv.id

        with get_session() as session:
            ConversationRepository(session).delete(conv_id, regular_user.id)

        with get_session() as session:
            assert list(MessageRepository(session).list_for_conversation(conv_id)) == []
