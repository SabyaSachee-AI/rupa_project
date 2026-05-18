"""Structured logging setup using structlog.

Configures structlog with two output formats:
- ``console``: human-readable colorised output for local dev
- ``json``:    one-JSON-object-per-line for prod log aggregators

Also wires the standard library logging module to route through structlog
so third-party loggers (sqlalchemy, openai, etc.) are formatted consistently.
"""

from __future__ import annotations

import logging
import sys
from typing import Any, cast

import structlog
from structlog.types import EventDict, Processor

from app.config import get_settings


def _add_app_context(_: Any, __: str, event_dict: EventDict) -> EventDict:
    """Inject application-wide context into every log entry."""

    settings = get_settings()
    event_dict.setdefault("env", settings.env.value)
    event_dict.setdefault("app", "rupa-ai")
    return event_dict


def _drop_color_message_key(_: Any, __: str, event_dict: EventDict) -> EventDict:
    """Remove the ``color_message`` key that uvicorn-style loggers inject."""

    event_dict.pop("color_message", None)
    return event_dict


def configure_logging() -> None:
    """Configure structlog and the standard library logging.

    Idempotent: safe to call multiple times (Streamlit reruns scripts often).
    """

    settings = get_settings()
    log_level = getattr(logging, settings.observability.log_level)

    shared_processors: list[Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso", utc=True),
        structlog.processors.StackInfoRenderer(),
        _drop_color_message_key,
        _add_app_context,
    ]

    if settings.observability.log_format == "json":
        renderer: Processor = structlog.processors.JSONRenderer()
        shared_processors.append(structlog.processors.format_exc_info)
    else:
        renderer = structlog.dev.ConsoleRenderer(colors=sys.stderr.isatty())

    structlog.configure(
        processors=[
            *shared_processors,
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        wrapper_class=structlog.make_filtering_bound_logger(log_level),
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    formatter = structlog.stdlib.ProcessorFormatter(
        foreign_pre_chain=shared_processors,
        processors=[
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            renderer,
        ],
    )

    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(formatter)

    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(log_level)

    for noisy in ("urllib3", "openai._base_client", "httpx", "httpcore"):
        logging.getLogger(noisy).setLevel(logging.WARNING)


def get_logger(name: str | None = None) -> structlog.stdlib.BoundLogger:
    """Return a bound structlog logger.

    Prefer module-level ``logger = get_logger(__name__)``.
    """

    return cast(structlog.stdlib.BoundLogger, structlog.get_logger(name))
