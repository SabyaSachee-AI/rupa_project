# Changelog

All notable changes to Rupa AI are documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [1.0.0] - 2026-05-18

The enterprise-grade rewrite. The original 164-line prototype is reorganised
into a layered, tested, observable, multi-user application.

### Added

- **Multi-layer architecture** under `app/`: `services/`, `db/`, `ui/`, `auth/`, `utils/`.
- **Authentication subsystem** (`app/auth/`):
  - bcrypt password hashing
  - login, registration, role-based authorization
  - bootstrap admin auto-created on first boot
- **Persistent storage** (`app/db/`) via SQLAlchemy 2.0:
  - `User`, `Conversation`, `Message` models with cascade deletes
  - Repository pattern (`UserRepository`, `ConversationRepository`, `MessageRepository`)
  - Per-user data isolation enforced at the repo layer
  - Alembic migrations
- **Admin console** page: list users, deactivate accounts, create users.
- **Conversation management**: multi-conversation sidebar per user, new chat,
  switch, automatic titling from first user message.
- **Streaming chat orchestrator** (`ChatService`): rate-limits, persists,
  injects RAG context, and streams tokens through one method.
- **Persistent sliding-window rate limiter** backed by message counts.
- **Custom exception hierarchy** (`RupaError` and subclasses) carrying both
  `log_message` and `user_message`.
- **Structured logging** via structlog with JSON / console formats.
- **Sentry integration** (optional, env-var driven).
- **Production configuration** via Pydantic Settings (`app/config.py`).
- **Tests**: 50+ unit tests + 1 multi-step integration test, ~60%+ coverage.
- **CI pipeline** (`.github/workflows/ci.yml`):
  - lint (ruff) + format (ruff format) + type check (mypy)
  - pytest on Python 3.10 / 3.11 / 3.12
  - Docker build smoke test
  - pip-audit + bandit security scans
- **Multi-stage Dockerfile** with non-root user and healthcheck.
- **`docker-compose.yml`** for local stack (optional Postgres).
- **Pre-commit hooks** (ruff, mypy, detect-secrets, file hygiene).
- **CLI** (`rupa`): `init-db`, `create-admin`, `login-test`, `version`.
- **Comprehensive docs**: `README.md`, `ARCHITECTURE.md`, `CONTRIBUTING.md`.

### Changed

- **Project layout**: `main.py` (164 lines) split into ~30 modules under `app/`.
- **Dependency manifest**: `requirements.txt` replaced by `pyproject.toml`
  with pinned compatible ranges. Build backend is hatchling.
- **Voice output**: per-user UUID-based MP3 files in `data/cache/` instead of
  the shared `rupa_speech.mp3` (concurrency bug fix).
- **Embeddings**: now prefer real OpenAI API endpoint when `OPENAI_API_KEY`
  is set, falling back to OpenRouter with a warning.
- **Sessions**: chat history now persists across restarts in the database
  instead of evaporating with the Streamlit session.

### Fixed

- Unclosed `<audio>` HTML element in the audio autoplayer.
- Two bare `except:` clauses that silently swallowed errors.
- Audio cache collision when multiple users use the app concurrently.
- README typos (`ython` -> `python`, broken markdown links).

### Security

- API keys no longer editable in the UI in production (gated behind
  `RUPA_ENV != production`).
- All passwords hashed with bcrypt cost 12.
- CSRF protection enabled in Streamlit config.
- Per-user rate limiting prevents API quota abuse.
- `detect-secrets` baseline + pre-commit hook to block accidental secret commits.

### Removed

- Prototype `main.py` (replaced by `app/main.py`).
- Prototype `vector_db.py` (replaced by `app/services/rag.py`).
- Tracked `rupa_speech.mp3` artifact.
- `note.md` (deployment instructions moved into `README.md`).

[Unreleased]: https://github.com/sabyasacheedas/rupa-ai/compare/v1.0.0...HEAD
[1.0.0]: https://github.com/sabyasacheedas/rupa-ai/releases/tag/v1.0.0
