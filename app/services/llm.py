"""LLM chat completions (OpenRouter).

Exposes a single high-level method, :meth:`LLMService.stream_chat`, returning
an iterator of token deltas. Retries transient failures via :mod:`tenacity`.
"""

from __future__ import annotations

from collections.abc import Iterable, Iterator
from typing import Any

from openai import APIConnectionError, APIError, OpenAI
from openai import RateLimitError as _OpenAIRateLimitError
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from app.config import get_settings
from app.exceptions import LLMConfigurationError, LLMError, LLMRateLimitError
from app.logging_setup import get_logger
from app.runtime_keys import get_openrouter_api_key

logger = get_logger(__name__)


ChatMessage = dict[str, str]


class LLMService:
    """Thin, testable wrapper around the OpenAI-compatible OpenRouter client."""

    def __init__(self) -> None:
        settings = get_settings()
        api_key = get_openrouter_api_key()
        if not api_key:
            raise LLMConfigurationError(
                "OpenRouter API key is not configured. Add it in the sidebar under API keys."
            )

        self._client = OpenAI(api_key=api_key, base_url=settings.llm.openrouter_base_url)
        self._model = settings.llm.chat_model
        self._max_tokens = settings.llm.max_response_tokens

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def stream_chat(
        self,
        messages: Iterable[ChatMessage],
        *,
        model: str | None = None,
        max_tokens: int | None = None,
    ) -> Iterator[str]:
        """Stream token deltas from the model.

        Yields:
            Each non-empty content delta string. Concatenate to reconstruct
            the full response.

        Raises:
            LLMRateLimitError, LLMError: on provider errors after retries.
        """

        try:
            yield from self._stream_with_retry(
                list(messages),
                model or self._model,
                max_tokens or self._max_tokens,
            )
        except _OpenAIRateLimitError as exc:
            logger.warning("llm.rate_limited", error=str(exc))
            raise LLMRateLimitError("LLM provider rate-limited the request", cause=exc) from exc
        except (APIConnectionError, APIError) as exc:
            logger.exception("llm.api_error")
            raise LLMError(f"LLM API error: {exc}", cause=exc) from exc
        except LLMError:
            raise
        except Exception as exc:
            logger.exception("llm.unexpected_error")
            raise LLMError(f"Unexpected LLM error: {exc}", cause=exc) from exc

    # ------------------------------------------------------------------
    # Internal: retried streaming
    # ------------------------------------------------------------------
    @retry(
        reraise=True,
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=8),
        retry=retry_if_exception_type((APIConnectionError,)),
    )
    def _stream_with_retry(
        self,
        messages: list[ChatMessage],
        model: str,
        max_tokens: int,
    ) -> Iterator[str]:
        logger.debug("llm.stream_start", model=model, message_count=len(messages))
        stream: Any = self._client.chat.completions.create(
            model=model,
            messages=messages,
            stream=True,
            max_tokens=max_tokens,
        )
        for chunk in stream:
            try:
                delta = chunk.choices[0].delta.content
            except (AttributeError, IndexError):
                continue
            if delta:
                yield delta


__all__ = ["ChatMessage", "LLMService"]
