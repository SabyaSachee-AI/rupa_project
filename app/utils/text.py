"""Text manipulation helpers (sanitisation, truncation, language detection)."""

from __future__ import annotations

import re

_TTS_ALLOWED_CHARS = re.compile(r"[^\w\s\u0980-\u09FF.,?!]")
_WHITESPACE = re.compile(r"\s+")
_BANGLA_CHAR = re.compile(r"[\u0980-\u09FF]")


def sanitise_for_tts(text: str) -> str:
    """Strip characters that confuse TTS engines.

    Keeps:
    - ASCII alphanumerics & whitespace
    - Bangla block (U+0980 .. U+09FF)
    - basic punctuation: . , ? !
    """

    cleaned = _TTS_ALLOWED_CHARS.sub("", text or "")
    cleaned = _WHITESPACE.sub(" ", cleaned).strip()
    return cleaned


def detect_language(text: str) -> str:
    """Return ``"Bangla"`` if any Bangla character is present, else ``"English"``."""

    return "Bangla" if _BANGLA_CHAR.search(text or "") else "English"


def truncate(text: str, *, max_chars: int, suffix: str = "...") -> str:
    """Truncate ``text`` to ``max_chars`` with an ellipsis suffix."""

    if len(text) <= max_chars:
        return text
    return text[: max_chars - len(suffix)].rstrip() + suffix


def derive_conversation_title(first_user_message: str, *, max_chars: int = 60) -> str:
    """Generate a short conversation title from the first user message."""

    flat = _WHITESPACE.sub(" ", (first_user_message or "").strip())
    if not flat:
        return "New conversation"
    return truncate(flat, max_chars=max_chars)
