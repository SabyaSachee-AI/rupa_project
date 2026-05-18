"""Main chat page."""

from __future__ import annotations

import streamlit as st

from app.auth import AuthenticatedUser
from app.db import get_session
from app.db.repositories import ConversationRepository
from app.exceptions import (
    LLMConfigurationError,
    LLMError,
    RateLimitError,
    RupaError,
    ValidationError,
)
from app.logging_setup import get_logger
from app.services.chat import ChatService
from app.services.llm import LLMService
from app.services.rag import RAGService
from app.services.stt import SpeechToTextService
from app.services.tts import TextToSpeechService
from app.ui.components.audio_player import autoplay_audio
from app.ui.components.chat_window import (
    render_history,
    render_user_message,
    stream_assistant_response,
)
from app.ui.components.sidebar import DEFAULT_PERSONA, render_sidebar
from app.ui.components.voice_input import render_hold_to_talk_mic
from app.ui.styles import inject_chat_styles, render_chat_header, render_sidebar_reopen_control
from app.ui.ux import check_api_readiness, render_api_status_banner, sync_session_from_conversation

logger = get_logger(__name__)


def render_chat(user: AuthenticatedUser) -> None:
    """Render the chat page."""

    mood = st.session_state.get("mood", "Happy")
    inject_chat_styles(mood)

    page = render_sidebar(user)
    if page == "admin":
        return

    render_sidebar_reopen_control()

    _ensure_active_conversation(user)

    render_api_status_banner()
    if not check_api_readiness().can_chat:
        st.info(
            "👈 Add your **OpenRouter** key in the sidebar under **🔧 Developer**, then try again."
        )
        st.stop()

    active_id = st.session_state["active_conversation_id"]
    with get_session() as session:
        conv = ConversationRepository(session).get_for_user(active_id, user.id)
        if conv is None:
            del st.session_state["active_conversation_id"]
            st.rerun()
            return
        if st.session_state.get("_loaded_conv_id") != active_id:
            sync_session_from_conversation(conv)
            st.session_state["_loaded_conv_id"] = active_id
        _sync_conversation_settings(conv.id, conv.user_id)
        snapshot = conv

    render_chat_header(
        title=snapshot.title,
        mood=snapshot.mood,
        language=snapshot.language,
        username=user.username,
    )

    render_history(snapshot)

    user_query = _collect_user_message()
    if not user_query:
        return

    render_user_message(user_query)

    try:
        chat_service = _build_chat_service()
        stream = chat_service.stream_turn(
            user_id=user.id,
            conversation_id=active_id,
            user_message=user_query,
        )
        full_response = stream_assistant_response(stream)
    except RateLimitError as exc:
        mins = max(1, exc.retry_after_seconds // 60)
        st.error(f"{exc.user_message} Please wait about {mins} minute(s).")
        return
    except ValidationError as exc:
        st.error(exc.user_message)
        return
    except LLMConfigurationError as exc:
        st.error(exc.user_message)
        with st.expander("Technical details"):
            st.code(exc.log_message)
        return
    except LLMError as exc:
        st.error(exc.user_message)
        return
    except RupaError as exc:
        st.error(exc.user_message)
        return

    st.toast("Reply ready")
    if full_response and not st.session_state.get("is_muted", False):
        _play_assistant_voice(full_response)

    st.rerun()


def _ensure_active_conversation(user: AuthenticatedUser) -> None:
    if st.session_state.get("active_conversation_id"):
        return

    with get_session() as session:
        repo = ConversationRepository(session)
        existing = repo.list_for_user(user.id, limit=1)
        if existing:
            conv = existing[0]
            st.session_state["active_conversation_id"] = conv.id
            sync_session_from_conversation(conv)
            return

        conv = repo.create(
            user_id=user.id,
            persona=st.session_state.get("custom_persona", DEFAULT_PERSONA),
            mood=st.session_state.get("mood", "Happy"),
            language=st.session_state.get("language", "Bangla"),
        )
        st.session_state["active_conversation_id"] = conv.id


def _sync_conversation_settings(conversation_id: str, user_id: str) -> None:
    desired_mood = st.session_state.get("mood")
    desired_lang = st.session_state.get("language")
    desired_persona = st.session_state.get("custom_persona")

    with get_session() as session:
        repo = ConversationRepository(session)
        conv = repo.get_for_user(conversation_id, user_id)
        if conv is None:
            return
        if desired_mood and conv.mood != desired_mood:
            conv.mood = desired_mood
        if desired_lang and conv.language != desired_lang:
            conv.language = desired_lang
        if desired_persona and conv.persona != desired_persona:
            conv.persona = desired_persona


def _collect_user_message() -> str | None:
    pending = st.session_state.pop("pending_user_message", None)
    if pending:
        return str(pending).strip()

    audio = st.session_state.pop("pending_voice_audio", None)
    if audio and isinstance(audio, dict) and audio.get("bytes"):
        with st.spinner("Transcribing your voice…"):
            try:
                stt = SpeechToTextService()
                fmt = str(audio.get("format") or "webm")
                filename = f"audio.{fmt.split(';', maxsplit=1)[0]}"
                text = stt.transcribe(audio["bytes"], filename=filename)
                st.toast("Voice transcribed")
                return text
            except RupaError as exc:
                st.warning(f"Voice input failed: {exc.user_message}")

    language = st.session_state.get("language", "Bangla")
    placeholder = "এখানে লিখুন…" if language == "Bangla" else "Message Rupa…"

    mic_col, input_col = st.columns([1, 11], gap="small", vertical_alignment="bottom")
    with mic_col:
        render_hold_to_talk_mic()
    with input_col:
        typed = st.chat_input(placeholder)
    return typed.strip() if typed else None


def _build_chat_service() -> ChatService:
    llm = LLMService()
    try:
        rag: RAGService | None = RAGService()
    except RupaError as exc:
        logger.info("ui.rag_disabled", reason=str(exc))
        rag = None
    return ChatService(llm=llm, rag=rag)


def _play_assistant_voice(text: str) -> None:
    try:
        tts = TextToSpeechService()
        path = tts.synthesise(
            text,
            language=st.session_state.get("language", "Bangla"),
            mood=st.session_state.get("mood", "Happy"),
            session_id=st.session_state.get("active_conversation_id"),
        )
    except RupaError as exc:
        logger.warning("ui.tts_failed", error=str(exc))
        return
    autoplay_audio(path)
