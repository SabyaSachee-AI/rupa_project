"""Sidebar: navigation, chats, settings."""

from __future__ import annotations

from collections.abc import Sequence
from contextlib import suppress

import streamlit as st

from app.auth import AuthenticatedUser
from app.config import get_settings
from app.db import get_session
from app.db.models import Conversation
from app.db.repositories import ConversationRepository
from app.exceptions import RAGError
from app.logging_setup import get_logger
from app.services.rag import RAGService
from app.ui.components.api_keys import render_api_keys_panel
from app.ui.components.nav import render_app_nav
from app.ui.styles import render_sidebar_brand
from app.ui.ux import check_api_readiness, format_relative_time, sync_session_from_conversation
from app.utils.rate_limit import RateLimiter

logger = get_logger(__name__)

DEFAULT_PERSONA = (
    "তুমি রূপা। মজিবর রহমানের প্রাক্তণ প্রেমিকা। উত্তর হবে সবসময় ২ বাক্যের মধ্যে খুব সংক্ষিপ্ত এবং সুনির্দিষ্ট।"
)


def render_sidebar(user: AuthenticatedUser) -> str:
    """Render sidebar. Returns current page (``chat`` or ``admin``)."""

    with st.sidebar:
        page = render_app_nav(user)
        st.divider()

        render_sidebar_brand(user.username, is_admin=user.is_admin)

        if page == "admin":
            render_api_keys_panel(expanded=False)
            st.caption("You are in the admin area. Use the switcher above to return to chat.")
            _render_sidebar_footer(user)
            return page

        render_api_keys_panel(expanded=not check_api_readiness().can_chat)
        _render_conversation_picker(user)
        st.divider()
        _render_quick_settings()
        _render_advanced_settings(user)
        st.divider()
        _render_sidebar_footer(user)

    return page


def _render_conversation_picker(user: AuthenticatedUser) -> None:
    st.markdown("#### 💬 Your chats")

    ncol1, ncol2 = st.columns([1, 1])
    with ncol1:
        if st.button("New", use_container_width=True, type="primary", key="new_conv_btn"):
            _create_conversation(user)
            st.toast("New chat started")
            st.rerun()
    with ncol2:
        if st.button("Refresh", use_container_width=True, key="refresh_conv_btn"):
            st.rerun()

    with get_session() as session:
        repo = ConversationRepository(session)
        conversations: Sequence[Conversation] = list(repo.list_for_user(user.id, limit=50))

    if not conversations:
        st.info("No chats yet. Tap **New** to begin.")
        return

    active_id = st.session_state.get("active_conversation_id")
    id_list = [c.id for c in conversations]
    labels = {
        c.id: f"{c.title[:32]}{'…' if len(c.title) > 32 else ''} · {format_relative_time(c.updated_at)}"
        for c in conversations
    }

    try:
        default_index = id_list.index(active_id) if active_id in id_list else 0
    except ValueError:
        default_index = 0

    picked = st.selectbox(
        "Open chat",
        options=id_list,
        index=default_index,
        format_func=lambda cid: labels.get(cid, cid),
        label_visibility="collapsed",
        key="conv_selectbox",
    )

    if picked and picked != active_id:
        conv = next(c for c in conversations if c.id == picked)
        st.session_state["active_conversation_id"] = picked
        sync_session_from_conversation(conv)
        st.rerun()

    _render_manage_current_chat(user, active_id or picked)


def _render_manage_current_chat(user: AuthenticatedUser, conversation_id: str | None) -> None:
    if not conversation_id:
        return

    with st.expander("Manage this chat", expanded=False):
        with get_session() as session:
            repo = ConversationRepository(session)
            conv = repo.get_for_user(conversation_id, user.id)
            if conv is None:
                return
            current_title = conv.title

        new_title = st.text_input("Title", value=current_title, key="rename_conv_input")
        c1, c2 = st.columns(2)
        with c1:
            if st.button("Save title", use_container_width=True, key="save_title_btn"):
                with get_session() as session:
                    ConversationRepository(session).rename(conversation_id, user.id, new_title)
                st.toast("Title updated")
                st.rerun()
        with c2:
            if st.button(
                "Delete chat", use_container_width=True, type="secondary", key="del_conv_btn"
            ):
                with get_session() as session:
                    ConversationRepository(session).delete(conversation_id, user.id)
                if st.session_state.get("active_conversation_id") == conversation_id:
                    del st.session_state["active_conversation_id"]
                st.toast("Chat deleted")
                st.rerun()


def _create_conversation(user: AuthenticatedUser) -> None:
    mood = st.session_state.get("mood", "Happy")
    language = st.session_state.get("language", "Bangla")
    persona = st.session_state.get("custom_persona", DEFAULT_PERSONA)

    with get_session() as session:
        repo = ConversationRepository(session)
        conv = repo.create(
            user_id=user.id,
            persona=persona,
            mood=mood,
            language=language,
        )
        st.session_state["active_conversation_id"] = conv.id

    logger.info("ui.conversation_created", user_id=user.id)


def _render_quick_settings() -> None:
    st.markdown("#### ⚙️ Quick settings")

    st.session_state["mood"] = st.radio(
        "Mood",
        ["Happy", "Sad"],
        horizontal=True,
        index=0 if st.session_state.get("mood", "Happy") == "Happy" else 1,
        key="mood_radio",
        help="Happy = warm tone · Sad = softer, emotional tone",
    )
    st.session_state["language"] = st.selectbox(
        "Reply language",
        ["Bangla", "English"],
        index=0 if st.session_state.get("language", "Bangla") == "Bangla" else 1,
        key="lang_select",
    )
    st.session_state["is_muted"] = not st.toggle(
        "Voice replies",
        value=not st.session_state.get("is_muted", False),
        help="Hear Rupa speak answers aloud",
        key="voice_toggle",
    )


def _render_advanced_settings(user: AuthenticatedUser) -> None:
    with st.expander("🎭 Persona & avatars", expanded=False):
        st.session_state["custom_persona"] = st.text_area(
            "How should Rupa behave?",
            value=st.session_state.get("custom_persona", DEFAULT_PERSONA),
            height=90,
            key="persona_text",
        )
        rupa_f = st.file_uploader("Rupa's avatar", type=["jpg", "png"], key="rupa_avatar_upload")
        user_f = st.file_uploader("Your avatar", type=["jpg", "png"], key="user_avatar_upload")
        if rupa_f is not None:
            st.session_state["rupa_avatar"] = rupa_f
        if user_f is not None:
            st.session_state["user_avatar"] = user_f

    with st.expander("🎤 Voice input", expanded=False):
        st.caption(
            "Use the **large mic button** next to the chat box at the bottom — "
            "**hold** while speaking, **release** to send."
        )
        r = check_api_readiness()
        if not r.can_voice_in:
            st.info("Add a **Groq** key under **🔧 Developer** to enable voice.")

    with st.expander("📚 Knowledge base", expanded=False):
        _render_knowledge_base(user)

    with st.expander("❓ Quick guide", expanded=False):
        st.markdown(
            """
            1. **New** — start a fresh chat
            2. **Type** at the bottom or **hold the mic** to talk
            3. **Mood / language** — change anytime in settings
            4. **Persona** — customize Rupa's personality
            """
        )
        r = check_api_readiness()
        st.caption(
            f"Status: Chat {'✓' if r.can_chat else '✗'} · "
            f"Voice {'✓' if r.can_voice_in else '-'} · "
            f"Docs {'✓' if r.can_rag else '-'} (see **API keys** above)"
        )


def _render_knowledge_base(user: AuthenticatedUser) -> None:
    st.caption("Upload PDF or DOCX — Rupa will use them when answering.")
    docs = st.file_uploader(
        "Documents",
        accept_multiple_files=True,
        type=["pdf", "docx"],
        key="kb_upload",
        label_visibility="collapsed",
    )
    if st.button("Index documents", use_container_width=True, key="teach_btn"):
        if not docs:
            st.warning("Choose at least one file first.")
            return
        try:
            rag = RAGService()
        except Exception as exc:
            st.error(f"Knowledge base unavailable: {exc}")
            return
        with st.spinner("Indexing your documents…"):
            try:
                result = rag.ingest(list(docs))
            except RAGError as exc:
                st.error(exc.user_message)
                return
        st.toast(f"Indexed {result.chunks_uploaded} sections")
        st.success(f"Ready — {result.total_vectors_in_index} items in knowledge base.")
        logger.info(
            "ui.kb_ingest",
            user_id=user.id,
            files=result.files_processed,
            chunks=result.chunks_uploaded,
        )


def _render_sidebar_footer(user: AuthenticatedUser) -> None:
    with suppress(Exception):
        remaining = RateLimiter().remaining(user.id)
        total = get_settings().rate_limit.messages
        if remaining <= total * 0.2:
            st.warning(f"Only **{remaining}** messages left in this window.")
        else:
            st.caption(f"💬 {remaining} of {total} messages available")

    if st.button("Sign out", use_container_width=True, type="secondary", key="logout_btn"):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()
