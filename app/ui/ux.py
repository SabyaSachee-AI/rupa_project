"""UX helpers: status checks, formatting, session sync."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

import streamlit as st

from app.db.models import Conversation
from app.runtime_keys import (
    get_groq_api_key,
    get_openai_api_key,
    get_openrouter_api_key,
    get_pinecone_api_key,
)


@dataclass(frozen=True, slots=True)
class ApiReadiness:
    """Which external services are configured."""

    openrouter: bool
    groq: bool
    openai: bool
    pinecone: bool

    @property
    def can_chat(self) -> bool:
        return self.openrouter

    @property
    def can_voice_in(self) -> bool:
        return self.groq

    @property
    def can_rag(self) -> bool:
        return self.pinecone and (self.openai or self.openrouter)


def check_api_readiness() -> ApiReadiness:
    return ApiReadiness(
        openrouter=bool(get_openrouter_api_key()),
        groq=bool(get_groq_api_key()),
        openai=bool(get_openai_api_key()),
        pinecone=bool(get_pinecone_api_key()),
    )


def render_api_status_banner() -> None:
    """Show a compact banner when required API keys are missing."""

    r = check_api_readiness()
    if r.can_chat:
        return

    st.error(
        "**Chat needs an OpenRouter key.** Open the sidebar → **🔧 Developer**, "
        "paste your key under **OpenRouter**, then continue chatting.",
        icon="⚠️",
    )
    with st.expander("Which key goes where?"):
        st.markdown(
            """
            | Feature | Enter in Developer panel |
            |---------|--------------------------|
            | **Chat** (required) | OpenRouter |
            | Voice input | Groq |
            | Knowledge base | Pinecone + OpenAI |
            """
        )


def format_relative_time(dt: datetime) -> str:
    """Human-readable relative time (e.g. '2h ago')."""

    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    now = datetime.now(timezone.utc)
    seconds = int((now - dt).total_seconds())
    if seconds < 60:
        return "just now"
    if seconds < 3600:
        return f"{seconds // 60}m ago"
    if seconds < 86400:
        return f"{seconds // 3600}h ago"
    if seconds < 604800:
        return f"{seconds // 86400}d ago"
    return dt.strftime("%b %d")


def sync_session_from_conversation(conv: Conversation) -> None:
    """Load conversation settings into session state when switching chats."""

    st.session_state["mood"] = conv.mood
    st.session_state["language"] = conv.language
    st.session_state["custom_persona"] = conv.persona


def suggested_prompts(language: str) -> list[str]:
    if language == "Bangla":
        return [
            "আজ তুমি কেমন আছো?",
            "আমার সম্পর্কে একটু বলো।",
            "একটা ছোট গল্প শোনাও।",
        ]
    return [
        "How are you today?",
        "Tell me something about yourself.",
        "Share a short story with me.",
    ]


def render_suggested_prompts(language: str) -> None:
    """Clickable starter prompts for empty conversations."""

    st.caption("Try asking:")
    cols = st.columns(len(prompts := suggested_prompts(language)))
    for col, prompt in zip(cols, prompts, strict=True):
        with col:
            if st.button(
                prompt,
                key=f"suggest_{hash(prompt) % 10_000}",
                use_container_width=True,
                type="secondary",
            ):
                st.session_state["pending_user_message"] = prompt
                st.rerun()
