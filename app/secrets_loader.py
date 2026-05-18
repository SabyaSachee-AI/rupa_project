"""Load Streamlit Cloud secrets into os.environ for Pydantic settings."""

from __future__ import annotations

import os
from collections.abc import Mapping
from contextlib import suppress
from typing import Any

import streamlit as st

from app.config import get_settings


def _set_env(name: str, value: Any) -> None:
    if value is None or isinstance(value, dict | list):
        return
    os.environ[str(name)] = str(value)


def _walk(prefix: str, node: Any) -> None:
    if isinstance(node, Mapping):
        for key, value in node.items():
            child = f"{prefix}_{key}" if prefix else str(key)
            _walk(child, value)
        return
    key = prefix.upper()
    if key:
        _set_env(key, node)


def apply_streamlit_secrets_to_env() -> None:
    """Apply ``st.secrets`` so :func:`get_settings` sees API keys on Streamlit Cloud."""

    try:
        root = st.secrets
    except Exception:
        return

    with suppress(Exception):
        if not len(root):
            return

    _walk("", dict(root))
    get_settings.cache_clear()
