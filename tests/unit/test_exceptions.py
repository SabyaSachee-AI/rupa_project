"""Tests for the custom exception hierarchy."""

from __future__ import annotations

import pytest

from app.exceptions import (
    AuthError,
    InvalidCredentialsError,
    LLMError,
    LLMRateLimitError,
    RateLimitError,
    RupaError,
    ValidationError,
)


@pytest.mark.unit
class TestExceptionHierarchy:
    def test_all_inherit_from_rupa_error(self) -> None:
        assert issubclass(AuthError, RupaError)
        assert issubclass(InvalidCredentialsError, AuthError)
        assert issubclass(LLMError, RupaError)
        assert issubclass(LLMRateLimitError, LLMError)
        assert issubclass(ValidationError, RupaError)

    def test_default_user_message(self) -> None:
        err = LLMError("network down")
        assert err.user_message == LLMError.default_user_message
        assert err.log_message == "network down"

    def test_custom_user_message(self) -> None:
        err = LLMError("network down", user_message="LLM is napping.")
        assert err.user_message == "LLM is napping."

    def test_cause_chained(self) -> None:
        cause = ValueError("inner")
        err = LLMError("outer", cause=cause)
        assert err.__cause__ is cause

    def test_rate_limit_has_retry_after(self) -> None:
        err = RateLimitError("too many", retry_after_seconds=120)
        assert err.retry_after_seconds == 120
        with pytest.raises(RateLimitError):
            raise err

    def test_subclass_can_be_caught_as_parent(self) -> None:
        with pytest.raises(AuthError):
            raise InvalidCredentialsError("bad")
        with pytest.raises(RupaError):
            raise LLMRateLimitError("rate")
