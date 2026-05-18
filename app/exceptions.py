"""Custom exception hierarchy.

All application-level errors derive from :class:`RupaError` so callers can
catch them uniformly while still distinguishing specific failure modes.
Each exception carries a ``user_message`` suitable for display in the UI
and a ``log_message`` with technical detail for operators.
"""

from __future__ import annotations


class RupaError(Exception):
    """Base class for all Rupa AI errors."""

    default_user_message: str = "Something went wrong. Please try again."

    def __init__(
        self,
        log_message: str,
        *,
        user_message: str | None = None,
        cause: Exception | None = None,
    ) -> None:
        super().__init__(log_message)
        self.log_message = log_message
        self.user_message = user_message or self.default_user_message
        self.__cause__ = cause


# ---------------------------------------------------------------------------
# Authentication
# ---------------------------------------------------------------------------
class AuthError(RupaError):
    """Base authentication / authorization error."""

    default_user_message = "Authentication failed."


class InvalidCredentialsError(AuthError):
    default_user_message = "Invalid username or password."


class PermissionDeniedError(AuthError):
    default_user_message = "You do not have permission to perform this action."


class UserAlreadyExistsError(AuthError):
    default_user_message = "A user with that username or email already exists."


# ---------------------------------------------------------------------------
# LLM / external services
# ---------------------------------------------------------------------------
class LLMError(RupaError):
    """Error talking to an LLM provider."""

    default_user_message = "The AI is having trouble responding. Please try again shortly."


class LLMRateLimitError(LLMError):
    default_user_message = "The AI provider rate-limited us. Please wait a moment."


class LLMConfigurationError(LLMError):
    default_user_message = "AI provider is not configured correctly. Contact your administrator."


# ---------------------------------------------------------------------------
# Speech
# ---------------------------------------------------------------------------
class STTError(RupaError):
    """Speech-to-text failure."""

    default_user_message = "Could not transcribe your audio. Please try again."


class TTSError(RupaError):
    """Text-to-speech failure."""

    default_user_message = "Could not generate voice output."


# ---------------------------------------------------------------------------
# RAG / vector DB
# ---------------------------------------------------------------------------
class RAGError(RupaError):
    """Vector-database / retrieval failure."""

    default_user_message = "Knowledge base is temporarily unavailable."


class RAGConfigurationError(RAGError):
    default_user_message = "Knowledge base is not configured."


class DocumentParsingError(RAGError):
    default_user_message = "Could not read one or more uploaded documents."


# ---------------------------------------------------------------------------
# Rate limiting & validation
# ---------------------------------------------------------------------------
class RateLimitError(RupaError):
    """User has exceeded their rate limit."""

    default_user_message = "You are sending messages too quickly. Please slow down."

    def __init__(
        self,
        log_message: str,
        *,
        retry_after_seconds: int,
        user_message: str | None = None,
    ) -> None:
        super().__init__(log_message, user_message=user_message)
        self.retry_after_seconds = retry_after_seconds


class ValidationError(RupaError):
    """User-supplied input failed validation."""

    default_user_message = "Your input is invalid."


# ---------------------------------------------------------------------------
# Persistence
# ---------------------------------------------------------------------------
class DatabaseError(RupaError):
    default_user_message = "A database error occurred. Please try again."


class NotFoundError(DatabaseError):
    default_user_message = "The requested resource was not found."
