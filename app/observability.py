"""Sentry initialisation and other observability bootstrap."""

from __future__ import annotations

from app.config import get_settings
from app.logging_setup import get_logger

logger = get_logger(__name__)


def init_sentry() -> None:
    """Initialise Sentry SDK if ``SENTRY_DSN`` is configured. No-op otherwise."""

    settings = get_settings()
    dsn = settings.observability.sentry_dsn.get_secret_value()
    if not dsn:
        return

    try:
        import sentry_sdk
        from sentry_sdk.integrations.logging import LoggingIntegration
    except ImportError:
        logger.warning("observability.sentry_sdk_not_installed")
        return

    sentry_sdk.init(
        dsn=dsn,
        environment=settings.env.value,
        release=f"rupa-ai@{_app_version()}",
        traces_sample_rate=settings.observability.sentry_traces_sample_rate,
        integrations=[
            LoggingIntegration(level=None, event_level=None),
        ],
        send_default_pii=False,
    )
    logger.info("observability.sentry_initialised", env=settings.env.value)


def _app_version() -> str:
    try:
        from app import __version__

        return __version__
    except ImportError:
        return "unknown"
