"""App navigation (chat / admin) for privileged users."""

from __future__ import annotations

import streamlit as st

from app.auth import AuthenticatedUser


def render_app_nav(user: AuthenticatedUser) -> str:
    """Render Chat / Admin switcher. Returns selected page id."""

    if not user.is_admin:
        return "chat"

    page = st.session_state.get("page", "chat")
    labels = {"chat": "💬 Chat", "admin": "⚙️ Admin"}

    if hasattr(st, "segmented_control"):
        choice = st.segmented_control(
            "Go to",
            options=["chat", "admin"],
            default=page,
            format_func=lambda p: labels[p],
            label_visibility="collapsed",
            key="app_nav_segment",
        )
    else:
        choice = st.radio(
            "Go to",
            options=["chat", "admin"],
            index=0 if page == "chat" else 1,
            format_func=lambda p: labels[p],
            horizontal=True,
            label_visibility="collapsed",
            key="app_nav_radio",
        )

    if choice:
        st.session_state["page"] = choice
        return str(choice)
    return str(page)
