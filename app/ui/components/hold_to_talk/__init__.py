"""Press-and-hold microphone custom component."""

from __future__ import annotations

import base64
import os
from typing import Any

import streamlit.components.v1 as components

_COMPONENT_NAME = "hold_to_talk"
_FRONTEND_DIR = os.path.join(os.path.dirname(__file__), "frontend")
_component = components.declare_component(_COMPONENT_NAME, path=_FRONTEND_DIR)


def hold_to_talk(*, disabled: bool = False, key: str | None = None) -> dict[str, Any] | None:
    """Record while the button is held; returns audio payload on release."""

    raw = _component(disabled=disabled, key=key, default=None)
    if not raw or not raw.get("audio_base64"):
        return None

    audio_bytes = base64.b64decode(raw["audio_base64"])
    return {
        "bytes": audio_bytes,
        "sample_rate": raw.get("sample_rate", 48000),
        "sample_width": raw.get("sample_width", 2),
        "format": raw.get("format", "webm"),
        "id": raw.get("id", 0),
    }
