"""Streamlit entrypoint.

Run with::

    streamlit run app/main.py
"""

from __future__ import annotations

import streamlit as st

from app.auth import AuthenticatedUser
from app.bootstrap import bootstrap
from app.ui.pages.admin import render_admin
from app.ui.pages.chat import render_chat
from app.ui.pages.login import render_login


def _page_config() -> None:
    st.set_page_config(
        page_title="Rupa AI",
        page_icon="💬",
        layout="wide",
        initial_sidebar_state="expanded",
        menu_items={
            "Get help": "https://github.com/sabyasacheedas/rupa-ai/issues",
            "Report a bug": "https://github.com/sabyasacheedas/rupa-ai/issues/new",
            "About": "Rupa AI — bilingual conversational assistant with memory and voice.",
        },
    )


def _current_user() -> AuthenticatedUser | None:
    user = st.session_state.get("user")
    if isinstance(user, AuthenticatedUser):
        return user
    return None


def main() -> None:
    _page_config()
    bootstrap()

    user = _current_user()
    if user is None:
        render_login()
        return

    page = st.session_state.get("page", "chat")
    if page == "admin" and user.is_admin:
        render_admin(user)
    else:
        render_chat(user)


if __name__ == "__main__":
    main()
