"""Tests for text utility helpers."""

from __future__ import annotations

import pytest

from app.utils.text import (
    derive_conversation_title,
    detect_language,
    sanitise_for_tts,
    truncate,
)


@pytest.mark.unit
class TestSanitiseForTts:
    def test_strips_symbols(self) -> None:
        assert sanitise_for_tts("Hello @world #python !") == "Hello world python !"

    def test_preserves_bangla(self) -> None:
        out = sanitise_for_tts("কেমন আছো? ভালো!")
        assert "কেমন" in out
        assert "?" in out
        assert "!" in out

    def test_collapses_whitespace(self) -> None:
        assert sanitise_for_tts("hello   \n\nworld") == "hello world"

    def test_empty_input(self) -> None:
        assert sanitise_for_tts("") == ""
        assert sanitise_for_tts("   ") == ""


@pytest.mark.unit
class TestDetectLanguage:
    def test_bangla_detected(self) -> None:
        assert detect_language("কেমন আছো?") == "Bangla"

    def test_english_detected(self) -> None:
        assert detect_language("Hello, world!") == "English"

    def test_mixed_returns_bangla(self) -> None:
        assert detect_language("Hello কেমন আছো") == "Bangla"

    def test_empty_returns_english(self) -> None:
        assert detect_language("") == "English"


@pytest.mark.unit
class TestTruncate:
    def test_short_unchanged(self) -> None:
        assert truncate("hello", max_chars=20) == "hello"

    def test_long_truncated_with_ellipsis(self) -> None:
        result = truncate("a" * 100, max_chars=10)
        assert len(result) == 10
        assert result.endswith("...")


@pytest.mark.unit
class TestDeriveTitle:
    def test_uses_first_line(self) -> None:
        assert derive_conversation_title("Hi there") == "Hi there"

    def test_collapses_whitespace(self) -> None:
        assert derive_conversation_title("Hello\n\nworld") == "Hello world"

    def test_empty_fallback(self) -> None:
        assert derive_conversation_title("") == "New conversation"
        assert derive_conversation_title("   ") == "New conversation"

    def test_truncates_long(self) -> None:
        out = derive_conversation_title("a" * 200, max_chars=60)
        assert len(out) == 60
