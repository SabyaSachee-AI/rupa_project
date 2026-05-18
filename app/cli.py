"""Command-line interface for administrative tasks.

Usage::

    rupa init-db             # create tables
    rupa create-admin USER EMAIL --password ...
    rupa version
"""

from __future__ import annotations

import argparse
import sys

from app import __version__
from app.auth import AuthService, hash_password
from app.bootstrap import bootstrap as _streamlit_bootstrap  # noqa: F401  (side-effect free import)
from app.db import get_session, init_db
from app.db.models import UserRole
from app.db.repositories import UserRepository
from app.logging_setup import configure_logging, get_logger


def _cmd_init_db(_: argparse.Namespace) -> int:
    init_db()
    print("Database schema initialised.")
    return 0


def _cmd_create_admin(ns: argparse.Namespace) -> int:
    with get_session() as session:
        UserRepository(session).create(
            username=ns.username.lower(),
            email=ns.email.lower(),
            hashed_password=hash_password(ns.password),
            role=UserRole.ADMIN,
        )
    print(f"Admin user {ns.username!r} created.")
    return 0


def _cmd_login_test(ns: argparse.Namespace) -> int:
    auth = AuthService()
    user = auth.login(ns.username, ns.password)
    print(f"Logged in as {user.username} ({user.role.value})")
    return 0


def _cmd_version(_: argparse.Namespace) -> int:
    print(f"rupa-ai {__version__}")
    return 0


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="rupa", description="Rupa AI admin CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    p_init = subparsers.add_parser("init-db", help="Create database schema")
    p_init.set_defaults(func=_cmd_init_db)

    p_admin = subparsers.add_parser("create-admin", help="Create an admin user")
    p_admin.add_argument("username")
    p_admin.add_argument("email")
    p_admin.add_argument("--password", required=True)
    p_admin.set_defaults(func=_cmd_create_admin)

    p_test = subparsers.add_parser("login-test", help="Test credentials")
    p_test.add_argument("username")
    p_test.add_argument("--password", required=True)
    p_test.set_defaults(func=_cmd_login_test)

    p_ver = subparsers.add_parser("version", help="Print version")
    p_ver.set_defaults(func=_cmd_version)

    return parser


def main(argv: list[str] | None = None) -> int:
    configure_logging()
    logger = get_logger(__name__)

    parser = _build_parser()
    ns = parser.parse_args(argv)
    try:
        return int(ns.func(ns))
    except Exception as exc:
        logger.exception("cli.error")
        print(f"Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
