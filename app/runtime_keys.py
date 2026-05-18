"""Runtime API keys: session overrides with .env / Streamlit secrets as defaults.

Keys entered in the sidebar **Developer** panel are stored in ``st.session_state``
and take priority over environment variables for the current browser session.
No app restart is required after saving keys in the UI.
"""

from __future__ import annotations

from contextlib import suppress
from typing import Any

from app.config import get_settings

# Session-state keys (also used as Streamlit widget keys)
KEY_OPENROUTER = "api_key_openrouter"
KEY_GROQ = "api_key_groq"
KEY_OPENAI = "api_key_openai"
KEY_PINECONE = "api_key_pinecone"
KEY_PINECONE_INDEX = "api_key_pinecone_index"
_INIT_FLAG = "_api_keys_initialized"


def _strip(value: str | None) -> str:
    return (value or "").strip()


def _secret_get(secrets: Any, name: str) -> str:
    try:
        return _strip(str(secrets.get(name, "")))
    except Exception:
        return ""


def _first_nonempty(*values: str | None) -> str:
    for v in values:
        s = _strip(v)
        if s:
            return s
    return ""


def ensure_api_keys_initialized() -> None:
    """Seed session keys from .env and Streamlit secrets once per session."""

    try:
        import streamlit as st
    except ImportError:
        return

    if st.session_state.get(_INIT_FLAG):
        return

    settings = get_settings()
    secrets: Any = {}
    with suppress(Exception):
        secrets = st.secrets

    # Legacy widget keys from earlier UI versions
    legacy_or = _strip(st.session_state.get("openrouter_override"))
    legacy_groq = _strip(st.session_state.get("groq_override"))

    defaults = {
        KEY_OPENROUTER: _first_nonempty(
            legacy_or,
            _secret_get(secrets, "OPENROUTER_API_KEY"),
            settings.llm.openrouter_api_key.get_secret_value(),
        ),
        KEY_GROQ: _first_nonempty(
            legacy_groq,
            _secret_get(secrets, "GROQ_API_KEY"),
            settings.llm.groq_api_key.get_secret_value(),
        ),
        KEY_OPENAI: _first_nonempty(
            _secret_get(secrets, "OPENAI_API_KEY"),
            settings.llm.openai_api_key.get_secret_value(),
        ),
        KEY_PINECONE: _first_nonempty(
            _secret_get(secrets, "PINECONE_API_KEY"),
            settings.rag.pinecone_api_key.get_secret_value(),
        ),
        KEY_PINECONE_INDEX: _first_nonempty(
            _secret_get(secrets, "PINECONE_INDEX_NAME"),
            settings.rag.pinecone_index_name,
        ),
    }

    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

    st.session_state[_INIT_FLAG] = True


def reload_api_keys_from_env() -> None:
    """Reset session keys from current .env / secrets (e.g. after editing .env file)."""

    try:
        import streamlit as st
    except ImportError:
        return

    get_settings.cache_clear()
    st.session_state.pop(_INIT_FLAG, None)
    for k in (KEY_OPENROUTER, KEY_GROQ, KEY_OPENAI, KEY_PINECONE, KEY_PINECONE_INDEX):
        st.session_state.pop(k, None)
    ensure_api_keys_initialized()


def _use_streamlit_session_keys() -> bool:
    """Use sidebar session keys only in a live Streamlit app (not in pytest)."""

    settings = get_settings()
    if settings.is_test:
        return False
    try:
        import streamlit as st

        return bool(getattr(st, "runtime", None) and st.runtime.exists())
    except Exception:
        return False


def get_openrouter_api_key() -> str:
    settings = get_settings()
    if not _use_streamlit_session_keys():
        return _strip(settings.llm.openrouter_api_key.get_secret_value())
    ensure_api_keys_initialized()
    import streamlit as st

    return _strip(st.session_state.get(KEY_OPENROUTER))


def get_groq_api_key() -> str:
    settings = get_settings()
    if not _use_streamlit_session_keys():
        return _strip(settings.llm.groq_api_key.get_secret_value())
    ensure_api_keys_initialized()
    import streamlit as st

    return _strip(st.session_state.get(KEY_GROQ))


def get_openai_api_key() -> str:
    settings = get_settings()
    if not _use_streamlit_session_keys():
        return _strip(settings.llm.openai_api_key.get_secret_value())
    ensure_api_keys_initialized()
    import streamlit as st

    return _strip(st.session_state.get(KEY_OPENAI))


def get_pinecone_api_key() -> str:
    settings = get_settings()
    if not _use_streamlit_session_keys():
        return _strip(settings.rag.pinecone_api_key.get_secret_value())
    ensure_api_keys_initialized()
    import streamlit as st

    return _strip(st.session_state.get(KEY_PINECONE))


def get_pinecone_index_name() -> str:
    settings = get_settings()
    if not _use_streamlit_session_keys():
        return settings.rag.pinecone_index_name
    ensure_api_keys_initialized()
    import streamlit as st

    name = _strip(st.session_state.get(KEY_PINECONE_INDEX))
    return name or settings.rag.pinecone_index_name
