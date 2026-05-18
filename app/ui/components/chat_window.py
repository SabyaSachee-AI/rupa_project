"""Chat window: history, streaming, empty state, starter prompts."""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

import streamlit as st

from app.db import get_session
from app.db.models import Conversation, MessageRole
from app.db.repositories import MessageRepository
from app.ui.styles import render_empty_chat_welcome
from app.ui.ux import render_suggested_prompts

DEFAULT_RUPA_AVATAR = "https://cdn-icons-png.flaticon.com/512/6833/6833591.png"
DEFAULT_USER_AVATAR = "https://cdn-icons-png.flaticon.com/512/3135/3135715.png"


def render_history(conversation: Conversation) -> bool:
    """Render messages. Returns True if any messages were shown."""

    user_avatar = st.session_state.get("user_avatar") or DEFAULT_USER_AVATAR
    rupa_avatar = st.session_state.get("rupa_avatar") or DEFAULT_RUPA_AVATAR

    with get_session() as session:
        msgs = list(MessageRepository(session).list_for_conversation(conversation.id))

    if not msgs:
        render_empty_chat_welcome(language=conversation.language)
        render_suggested_prompts(conversation.language)
        return False

    for msg in msgs:
        avatar: Any = rupa_avatar if msg.role is MessageRole.ASSISTANT else user_avatar
        with st.chat_message(msg.role.value, avatar=avatar):
            st.markdown(msg.content)
    return True


def stream_assistant_response(stream: Iterator[str]) -> str:
    """Stream assistant tokens with a typing indicator."""

    rupa_avatar = st.session_state.get("rupa_avatar") or DEFAULT_RUPA_AVATAR
    full_response = ""
    with st.chat_message("assistant", avatar=rupa_avatar):
        placeholder = st.empty()
        for delta in stream:
            full_response += delta
            placeholder.markdown(full_response + " ▌")
        placeholder.markdown(full_response)
    return full_response


def render_user_message(text: str) -> None:
    user_avatar = st.session_state.get("user_avatar") or DEFAULT_USER_AVATAR
    with st.chat_message("user", avatar=user_avatar):
        st.markdown(text)
