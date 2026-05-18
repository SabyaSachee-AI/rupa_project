# Contributing to Rupa AI

Thanks for taking the time to contribute. This guide gets you from a fresh
clone to a passing pull request.

## Quick start

```bash
git clone https://github.com/sabyasacheedas/rupa-ai.git
cd rupa-ai

python -m venv .venv
.venv\Scripts\activate              # Windows
# source .venv/bin/activate         # macOS / Linux

pip install -e ".[dev]"
pre-commit install

cp .env.example .env                 # fill in at least OPENROUTER_API_KEY for local testing

streamlit run app/main.py
```

## Quality gates

Run before pushing — CI runs the same:

```bash
ruff check app tests              # lint
ruff format --check app tests     # formatting
mypy app                          # type check
pytest -v                         # tests + coverage
```

All four must pass before a PR is merged.

## Project layout

See [ARCHITECTURE.md](ARCHITECTURE.md). In short:

- **`app/services/`** — Pure Python business logic. Easiest to write tests for.
- **`app/db/`** — SQLAlchemy models + repositories. Add new queries here.
- **`app/ui/`** — Streamlit pages and components. Never imports from `db/` directly.
- **`app/utils/`** — Cross-cutting helpers.
- **`tests/unit/`** — Fast, fully mocked tests.
- **`tests/integration/`** — Tests that exercise multiple services together.

## Adding a feature: typical flow

1. **Domain model** — add or update SQLAlchemy models in `app/db/models.py`.
2. **Migration** — generate with `alembic revision --autogenerate -m "describe change"`,
   review the diff in `alembic/versions/`, then `alembic upgrade head`.
3. **Repository** — add query helpers in `app/db/repositories.py`.
4. **Service** — add or extend a service in `app/services/`. Inject deps via
   constructor; raise typed exceptions from `app/exceptions.py`.
5. **UI** — wire it up in `app/ui/pages/` or `app/ui/components/`. Catch
   `RupaError` and display `exc.user_message`.
6. **Tests** — unit-test the service in isolation; add an integration test
   if the change spans multiple services.
7. **Docs** — update `README.md` and `ARCHITECTURE.md` if user-facing or
   structural; add a `CHANGELOG.md` entry.

## Coding standards

- **Python 3.10+** type hints everywhere. `mypy --strict` is enabled on `app/`.
- **No bare `except:`** clauses. Catch specific exceptions or `RupaError`.
- **Logging**: `from app.logging_setup import get_logger; logger = get_logger(__name__)`.
  Use `logger.info("event.name", key=value)` style — no f-strings inside log messages.
- **Errors**: raise `RupaError` subclasses with a clear `log_message` and
  optional friendly `user_message`.
- **Secrets**: never log them. Use `SecretStr` in config.
- **Comments**: don't narrate code. Explain non-obvious *why*.

## Commit messages

Conventional Commits:

```
feat(chat): stream tokens to UI in real time
fix(auth): reject inactive users at login
docs(readme): clarify deployment steps
chore(deps): bump streamlit to 1.41
test(rag): add ingest happy path
refactor(db): extract message repository
```

## Pull requests

- Keep PRs focused — ideally one logical change.
- Fill out the PR template (auto-loaded from `.github/PULL_REQUEST_TEMPLATE.md`).
- Link related issues with `Closes #N`.
- Wait for CI green before requesting review.

## Running the database

SQLite for local dev (default in `.env.example`). To use Postgres locally:

```bash
docker run --rm -d --name rupa-pg -p 5432:5432 \
    -e POSTGRES_USER=rupa -e POSTGRES_PASSWORD=rupa -e POSTGRES_DB=rupa \
    postgres:16-alpine

# In .env:
DATABASE_URL=postgresql+psycopg2://rupa:rupa@localhost:5432/rupa

pip install -e ".[postgres]"
alembic upgrade head
```

## Reporting bugs / requesting features

Open a GitHub issue with:

- Steps to reproduce
- Expected vs actual
- Environment (`rupa version`, OS, Python version)
- Relevant log lines (with secrets redacted)

## License

By contributing you agree your work is released under the [MIT License](LICENSE).
