"""Audio playback helper for assistant TTS output."""

from __future__ import annotations

import base64
from pathlib import Path

import streamlit as st


def autoplay_audio(path: Path | None) -> None:
    """Embed an autoplaying audio element. No-op if ``path`` is falsy or missing.

    Renders a properly-closed ``<audio>`` element (fixes the bug where the
    original prototype emitted an unclosed tag, breaking some browsers).
    """

    if path is None or not path.exists():
        return

    try:
        data = path.read_bytes()
    except OSError:
        return

    b64 = base64.b64encode(data).decode("ascii")
    st.markdown(
        f'<audio autoplay="true" src="data:audio/mp3;base64,{b64}"></audio>',
        unsafe_allow_html=True,
    )
