"""Application startup tasks: logging, DB, Sentry, bootstrap admin.

Designed to be called once per Streamlit script run (the first call performs
real work; subsequent calls short-circuit via a session-state flag).
"""

from __future__ import annotations

import streamlit as st
from dotenv import load_dotenv

from app.auth import bootstrap_admin_if_needed
from app.db import init_db
from app.logging_setup import configure_logging, get_logger
from app.observability import init_sentry
from app.runtime_keys import ensure_api_keys_initialized
from app.secrets_loader import apply_streamlit_secrets_to_env

_BOOTSTRAP_FLAG = "_rupa_bootstrap_done"


def bootstrap() -> None:
    """Run idempotent startup. Safe to call on every script execution."""

    if st.session_state.get(_BOOTSTRAP_FLAG):
        return

    load_dotenv(override=False)
    apply_streamlit_secrets_to_env()
    configure_logging()
    logger = get_logger(__name__)
    logger.info("app.bootstrap_start")

    init_sentry()
    init_db()
    bootstrap_admin_if_needed()
    ensure_api_keys_initialized()

    st.session_state[_BOOTSTRAP_FLAG] = True
    logger.info("app.bootstrap_done")
