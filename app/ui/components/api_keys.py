"""Sidebar panel: configure all API keys in the Developer section."""

from __future__ import annotations

import streamlit as st

from app.runtime_keys import (
    KEY_GROQ,
    KEY_OPENAI,
    KEY_OPENROUTER,
    KEY_PINECONE,
    KEY_PINECONE_INDEX,
    ensure_api_keys_initialized,
    reload_api_keys_from_env,
)
from app.ui.ux import check_api_readiness


def render_api_keys_panel(*, expanded: bool = False) -> None:
    """All provider keys in one place; applied immediately for this session."""

    ensure_api_keys_initialized()
    readiness = check_api_readiness()

    with st.expander("🔧 Developer", expanded=expanded or not readiness.can_chat):
        st.caption(
            "Keys apply **immediately** for this session. "
            "They are not written to disk unless you also add them to `.env`."
        )

        st.text_input(
            "OpenRouter — chat (required)",
            type="password",
            key=KEY_OPENROUTER,
            help="Powers text replies. Get one at openrouter.ai/keys",
        )
        st.text_input(
            "Groq — voice input",
            type="password",
            key=KEY_GROQ,
            help="Powers speech-to-text (Whisper). Get one at console.groq.com",
        )
        st.text_input(
            "OpenAI — embeddings",
            type="password",
            key=KEY_OPENAI,
            help="Recommended for knowledge-base search. platform.openai.com",
        )
        st.text_input(
            "Pinecone — vector database",
            type="password",
            key=KEY_PINECONE,
            help="Stores uploaded documents. app.pinecone.io",
        )
        st.text_input(
            "Pinecone index name",
            key=KEY_PINECONE_INDEX,
            help="Default: rupa-knowledge",
        )

        c1, c2 = st.columns(2)
        with c1:
            if st.button("Reload from .env", use_container_width=True, key="reload_env_keys"):
                reload_api_keys_from_env()
                st.toast("Reloaded keys from .env / secrets")
                st.rerun()
        with c2:
            if st.button("Clear all keys", use_container_width=True, key="clear_api_keys"):
                for k in (KEY_OPENROUTER, KEY_GROQ, KEY_OPENAI, KEY_PINECONE):
                    st.session_state[k] = ""
                st.toast("Cleared session keys")
                st.rerun()

        r = check_api_readiness()
        st.markdown(
            f"""
            **Status**
            - Chat: {"✅ ready" if r.can_chat else "❌ add OpenRouter key"}
            - Voice: {"✅ ready" if r.can_voice_in else "⚪ optional (Groq)"}
            - Knowledge base: {"✅ ready" if r.can_rag else "⚪ needs Pinecone + OpenAI"}
            """
        )
