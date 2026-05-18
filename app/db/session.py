"""SQLAlchemy engine and session management.

The engine is created lazily (so tests can override settings before first use)
and cached at module level. ``get_session`` is a context manager that yields
a transactional ``Session`` and commits/rolls back automatically.

For SQLite, ``check_same_thread=False`` is required because Streamlit reruns
script execution on a different thread than the one that created the engine.
"""

from __future__ import annotations

from collections.abc import Generator
from contextlib import contextmanager
from pathlib import Path

from sqlalchemy import Engine, create_engine, event
from sqlalchemy.engine import Connection
from sqlalchemy.orm import Session, sessionmaker

from app.config import get_settings
from app.db.models import Base
from app.logging_setup import get_logger

logger = get_logger(__name__)

_engine: Engine | None = None
_SessionLocal: sessionmaker[Session] | None = None


def _is_sqlite(url: str) -> bool:
    return url.startswith("sqlite")


def get_engine() -> Engine:
    """Return the process-wide SQLAlchemy engine (created on first call)."""

    global _engine, _SessionLocal
    if _engine is not None:
        return _engine

    settings = get_settings()
    url = settings.db.database_url

    if _is_sqlite(url):
        db_path = url.removeprefix("sqlite:///")
        if db_path and db_path != ":memory:":
            Path(db_path).parent.mkdir(parents=True, exist_ok=True)

        _engine = create_engine(
            url,
            echo=settings.db.echo_sql,
            connect_args={"check_same_thread": False},
            future=True,
        )

        @event.listens_for(_engine, "connect")
        def _enable_sqlite_fk(dbapi_conn: object, _: object) -> None:
            cursor = dbapi_conn.cursor()  # type: ignore[attr-defined]
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.execute("PRAGMA journal_mode=WAL")
            cursor.close()
    else:
        _engine = create_engine(
            url,
            echo=settings.db.echo_sql,
            pool_size=settings.db.pool_size,
            pool_pre_ping=True,
            future=True,
        )

    _SessionLocal = sessionmaker(
        bind=_engine,
        autoflush=False,
        autocommit=False,
        expire_on_commit=False,
        future=True,
    )

    logger.info("db.engine_created", url=_redact_url(url))
    return _engine


def _redact_url(url: str) -> str:
    """Hide password component for safe logging."""

    if "@" not in url:
        return url
    prefix, rest = url.split("://", 1)
    creds, host = rest.split("@", 1)
    if ":" in creds:
        user, _ = creds.split(":", 1)
        return f"{prefix}://{user}:***@{host}"
    return url


def init_db() -> None:
    """Create all tables. Safe to call on every startup (idempotent).

    For production use, prefer Alembic migrations; this is convenient for
    dev/SQLite where no migration history exists yet.
    """

    engine = get_engine()
    Base.metadata.create_all(engine)
    logger.info("db.schema_initialised")


@contextmanager
def get_session() -> Generator[Session, None, None]:
    """Yield a transactional Session.

    Commits on successful exit, rolls back on exception, always closes.

    Example::

        with get_session() as session:
            user = session.get(User, user_id)
            user.last_login_at = utcnow()
    """

    if _SessionLocal is None:
        get_engine()
    assert _SessionLocal is not None

    session = _SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def reset_engine_for_tests() -> None:
    """Dispose the cached engine. Call from test fixtures only."""

    global _engine, _SessionLocal
    if _engine is not None:
        _engine.dispose()
    _engine = None
    _SessionLocal = None


__all__ = ["Connection", "get_engine", "get_session", "init_db", "reset_engine_for_tests"]
