"""Tests for the LLM service (with the OpenRouter client mocked)."""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any
from unittest.mock import MagicMock

import pytest
from openai import APIConnectionError

from app.exceptions import LLMConfigurationError, LLMError
from app.services.llm import LLMService


def _mock_chunk(delta_content: str | None) -> Any:
    chunk = MagicMock()
    chunk.choices = [MagicMock()]
    chunk.choices[0].delta = MagicMock()
    chunk.choices[0].delta.content = delta_content
    return chunk


def _mock_stream(deltas: list[str | None]) -> Iterator[Any]:
    return iter(_mock_chunk(d) for d in deltas)


@pytest.fixture()
def llm_service(mocker: Any) -> LLMService:
    mock_client = MagicMock()
    mocker.patch("app.services.llm.OpenAI", return_value=mock_client)
    service = LLMService()
    service._client = mock_client  # type: ignore[attr-defined]
    return service


@pytest.mark.unit
class TestLLMService:
    def test_no_api_key_raises_configuration_error(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("OPENROUTER_API_KEY", "")
        from app.config import get_settings

        get_settings.cache_clear()
        with pytest.raises(LLMConfigurationError):
            LLMService()

    def test_stream_yields_token_deltas(self, llm_service: LLMService) -> None:
        client = llm_service._client  # type: ignore[attr-defined]
        client.chat.completions.create.return_value = _mock_stream(["He", "llo", " world"])

        result = list(llm_service.stream_chat([{"role": "user", "content": "hi"}]))
        assert "".join(result) == "Hello world"

    def test_stream_skips_none_deltas(self, llm_service: LLMService) -> None:
        client = llm_service._client  # type: ignore[attr-defined]
        client.chat.completions.create.return_value = _mock_stream(["A", None, "B", None, "C"])

        assert "".join(llm_service.stream_chat([])) == "ABC"

    def test_connection_error_translates_to_llm_error(self, llm_service: LLMService) -> None:
        client = llm_service._client  # type: ignore[attr-defined]
        client.chat.completions.create.side_effect = APIConnectionError(request=MagicMock())

        with pytest.raises(LLMError):
            list(llm_service.stream_chat([]))

    def test_passes_messages_to_provider(self, llm_service: LLMService) -> None:
        client = llm_service._client  # type: ignore[attr-defined]
        client.chat.completions.create.return_value = _mock_stream(["x"])

        messages = [
            {"role": "system", "content": "You are Rupa."},
            {"role": "user", "content": "Hi"},
        ]
        list(llm_service.stream_chat(messages))

        called_args = client.chat.completions.create.call_args
        assert called_args.kwargs["messages"] == messages
        assert called_args.kwargs["stream"] is True
