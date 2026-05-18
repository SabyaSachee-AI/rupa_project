"""Main-area press-and-hold voice input beside the chat box."""

from __future__ import annotations

import streamlit as st

from app.ui.components.hold_to_talk import hold_to_talk
from app.ui.ux import check_api_readiness

_LAST_HOLD_ID = "_last_hold_to_talk_id"


def render_hold_to_talk_mic(*, key: str = "rupa_hold_voice") -> bool:
    """Render the mic button. Returns True if a new recording was queued for submit."""

    ready = check_api_readiness().can_voice_in
    audio = hold_to_talk(disabled=not ready, key=key)

    if not audio or not audio.get("bytes"):
        return False

    rec_id = int(audio.get("id") or 0)
    if rec_id <= st.session_state.get(_LAST_HOLD_ID, 0):
        return False

    st.session_state[_LAST_HOLD_ID] = rec_id
    if "pending_voice_audio" not in st.session_state:
        st.session_state["pending_voice_audio"] = audio
        st.rerun()
    return True
