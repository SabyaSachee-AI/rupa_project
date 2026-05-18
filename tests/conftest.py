"""Shared pytest fixtures.

Every test runs against a fresh in-memory SQLite database so suites stay
fully isolated and don't touch the developer's real ``data/rupa.db``.
"""

from __future__ import annotations

import os
from collections.abc import Generator
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from app.auth import AuthenticatedUser

os.environ.setdefault("RUPA_ENV", "test")
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("AUTH_COOKIE_KEY", "test-cookie-key-for-test-only")
os.environ.setdefault("OPENROUTER_API_KEY", "test-or-key")
os.environ.setdefault("GROQ_API_KEY", "test-groq-key")
os.environ.setdefault("OPENAI_API_KEY", "test-openai-key")
os.environ.setdefault("PINECONE_API_KEY", "test-pinecone-key")
os.environ.setdefault("LOG_LEVEL", "WARNING")
os.environ.setdefault("LOG_FORMAT", "console")
os.environ.setdefault("BOOTSTRAP_ADMIN_PASSWORD", "BootstrapPass123!")


@pytest.fixture(autouse=True)
def _reset_settings_and_db() -> Generator[None, None, None]:
    """Reset the settings cache and DB engine between tests."""

    from app.config import get_settings
    from app.db.session import reset_engine_for_tests

    get_settings.cache_clear()
    reset_engine_for_tests()
    yield
    reset_engine_for_tests()
    get_settings.cache_clear()


@pytest.fixture()
def db_initialised() -> None:
    """Create schema in the in-memory DB for the current test."""

    from app.db import init_db

    init_db()


@pytest.fixture()
def admin_user(db_initialised: None) -> AuthenticatedUser:
    """Create and return an admin user."""

    from app.auth import AuthService
    from app.db.models import UserRole

    return AuthService().register(
        username="alice",
        email="alice@example.com",
        password="SuperSecret!23",
        role=UserRole.ADMIN,
    )


@pytest.fixture()
def regular_user(db_initialised: None) -> AuthenticatedUser:
    """Create and return a normal user."""

    from app.auth import AuthService

    return AuthService().register(
        username="bob",
        email="bob@example.com",
        password="AnotherSecret!23",
    )
