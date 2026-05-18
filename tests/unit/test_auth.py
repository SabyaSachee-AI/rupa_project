"""Tests for the auth service: password hashing, login, register, RBAC."""

from __future__ import annotations

import pytest

from app.auth import (
    AuthService,
    bootstrap_admin_if_needed,
    hash_password,
    verify_password,
)
from app.db import get_session
from app.db.models import UserRole
from app.db.repositories import UserRepository
from app.exceptions import (
    InvalidCredentialsError,
    PermissionDeniedError,
    UserAlreadyExistsError,
)


@pytest.mark.unit
class TestPasswordHashing:
    def test_round_trip(self) -> None:
        h = hash_password("hunter2")
        assert verify_password("hunter2", h)
        assert not verify_password("wrong", h)

    def test_empty_password_rejected(self) -> None:
        with pytest.raises(ValueError):
            hash_password("")

    def test_verify_bad_hash_returns_false(self) -> None:
        assert verify_password("x", "not-a-bcrypt-hash") is False
        assert verify_password("", "anything") is False

    def test_hashes_differ_per_call(self) -> None:
        assert hash_password("same-pw") != hash_password("same-pw")


@pytest.mark.unit
class TestAuthService:
    def test_register_then_login(self, db_initialised: None) -> None:
        auth = AuthService()
        registered = auth.register("alice", "alice@example.com", "VerySecret!23")
        assert registered.username == "alice"

        logged_in = auth.login("alice", "VerySecret!23")
        assert logged_in.id == registered.id

    def test_login_username_case_insensitive(self, db_initialised: None) -> None:
        auth = AuthService()
        auth.register("CaseUser", "case@example.com", "VerySecret!23")
        assert auth.login("caseUSER", "VerySecret!23").username == "caseuser"

    def test_login_bad_password(self, db_initialised: None) -> None:
        auth = AuthService()
        auth.register("alice", "alice@example.com", "VerySecret!23")
        with pytest.raises(InvalidCredentialsError):
            auth.login("alice", "wrong")

    def test_login_unknown_user(self, db_initialised: None) -> None:
        with pytest.raises(InvalidCredentialsError):
            AuthService().login("nobody", "x")

    def test_login_inactive_user(self, db_initialised: None) -> None:
        auth = AuthService()
        user = auth.register("alice", "alice@example.com", "VerySecret!23")
        with get_session() as session:
            UserRepository(session).set_active(user.id, is_active=False)
        with pytest.raises(InvalidCredentialsError):
            auth.login("alice", "VerySecret!23")

    def test_register_duplicate_username(self, db_initialised: None) -> None:
        auth = AuthService()
        auth.register("alice", "a1@example.com", "VerySecret!23")
        with pytest.raises(UserAlreadyExistsError):
            auth.register("alice", "a2@example.com", "VerySecret!23")

    def test_require_admin_passes(self, db_initialised: None) -> None:
        auth = AuthService()
        admin = auth.register("a", "a@example.com", "Pwd!23456", role=UserRole.ADMIN)
        result = auth.require_admin(admin)
        assert result is admin

    def test_require_admin_rejects_user(self, db_initialised: None) -> None:
        auth = AuthService()
        user = auth.register("a", "a@example.com", "Pwd!23456")
        with pytest.raises(PermissionDeniedError):
            auth.require_admin(user)

    def test_require_admin_rejects_none(self) -> None:
        with pytest.raises(PermissionDeniedError):
            AuthService().require_admin(None)


@pytest.mark.unit
class TestBootstrapAdmin:
    def test_creates_admin_when_empty(self, db_initialised: None) -> None:
        bootstrap_admin_if_needed()
        with get_session() as session:
            users = list(UserRepository(session).list_all())
        assert len(users) == 1
        assert users[0].role is UserRole.ADMIN

    def test_idempotent(self, db_initialised: None) -> None:
        bootstrap_admin_if_needed()
        bootstrap_admin_if_needed()
        with get_session() as session:
            assert UserRepository(session).count() == 1
