"""Authentication service.

Owns:
- Password hashing (bcrypt)
- Login / register
- Session state on Streamlit
- Role-based authorization checks

Design note: we do not use ``streamlit-authenticator``'s YAML-file user store
because we need a real database for the rest of the app anyway. We reuse its
cookie manager indirectly through Streamlit's ``session_state`` plus a signed
cookie via :mod:`streamlit_authenticator.utilities.hasher`-equivalent flow.
For simplicity, we use Streamlit's built-in session state which is sufficient
for small-team usage.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

import bcrypt

from app.config import get_settings
from app.db import get_session
from app.db.models import UserRole
from app.db.repositories import UserRepository
from app.exceptions import (
    InvalidCredentialsError,
    PermissionDeniedError,
)
from app.logging_setup import get_logger

if TYPE_CHECKING:
    pass

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Password hashing
# ---------------------------------------------------------------------------
_BCRYPT_ROUNDS = 12


def hash_password(plain: str) -> str:
    """Hash a password using bcrypt."""
    if not plain:
        raise ValueError("Password must not be empty")
    hashed: bytes = bcrypt.hashpw(plain.encode("utf-8"), bcrypt.gensalt(rounds=_BCRYPT_ROUNDS))
    return hashed.decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    """Constant-time verification of a password against its bcrypt hash."""
    if not plain or not hashed:
        return False
    try:
        return bool(bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8")))
    except ValueError:
        return False


# ---------------------------------------------------------------------------
# Authenticated user (immutable DTO carried in session)
# ---------------------------------------------------------------------------
@dataclass(frozen=True, slots=True)
class AuthenticatedUser:
    id: str
    username: str
    email: str
    role: UserRole

    @property
    def is_admin(self) -> bool:
        return self.role is UserRole.ADMIN


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------
class AuthService:
    """Authentication and authorization operations.

    Stateless: each method opens its own DB session. Cheap to instantiate
    per request.
    """

    def login(self, username: str, password: str) -> AuthenticatedUser:
        """Verify credentials and return an :class:`AuthenticatedUser`.

        Raises:
            InvalidCredentialsError: username unknown, password wrong, or
                account disabled.
        """

        username = (username or "").strip().lower()
        with get_session() as session:
            repo = UserRepository(session)
            user = repo.get_by_username(username)
            if user is None or not user.is_active:
                logger.warning("auth.login_failed", username=username, reason="unknown_or_inactive")
                raise InvalidCredentialsError(f"Login failed for username={username!r}")

            if not verify_password(password, user.hashed_password):
                logger.warning("auth.login_failed", username=username, reason="bad_password")
                raise InvalidCredentialsError(f"Login failed for username={username!r}")

            repo.record_login(user.id)
            logger.info("auth.login_success", user_id=user.id, username=user.username)

            return AuthenticatedUser(
                id=user.id,
                username=user.username,
                email=user.email,
                role=user.role,
            )

    def register(
        self,
        username: str,
        email: str,
        password: str,
        role: UserRole = UserRole.USER,
    ) -> AuthenticatedUser:
        """Create a new user. Raises :class:`UserAlreadyExistsError` on conflict."""

        username = (username or "").strip().lower()
        email = (email or "").strip().lower()

        with get_session() as session:
            repo = UserRepository(session)
            user = repo.create(
                username=username,
                email=email,
                hashed_password=hash_password(password),
                role=role,
            )
            logger.info("auth.user_registered", user_id=user.id, username=user.username)
            return AuthenticatedUser(
                id=user.id,
                username=user.username,
                email=user.email,
                role=user.role,
            )

    def require_admin(self, user: AuthenticatedUser | None) -> AuthenticatedUser:
        """Guard: raise :class:`PermissionDeniedError` if user is not admin."""

        if user is None or not user.is_admin:
            raise PermissionDeniedError("Admin role required")
        return user


# ---------------------------------------------------------------------------
# Bootstrap: ensure at least one admin user exists on first boot
# ---------------------------------------------------------------------------
def bootstrap_admin_if_needed() -> None:
    """Create the bootstrap admin if no users exist yet.

    Reads ``BOOTSTRAP_ADMIN_*`` env vars. Idempotent: does nothing if any
    user already exists in the DB.
    """

    settings = get_settings()
    with get_session() as session:
        repo = UserRepository(session)
        if repo.count() > 0:
            return

        repo.create(
            username=settings.auth.bootstrap_admin_username.lower(),
            email=settings.auth.bootstrap_admin_email.lower(),
            hashed_password=hash_password(
                settings.auth.bootstrap_admin_password.get_secret_value()
            ),
            role=UserRole.ADMIN,
        )
        logger.warning(
            "auth.bootstrap_admin_created",
            username=settings.auth.bootstrap_admin_username,
            email=settings.auth.bootstrap_admin_email,
            message="Change the bootstrap password after first login.",
        )
