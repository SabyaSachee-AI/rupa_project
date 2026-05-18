# Architecture

This document explains how Rupa AI is structured, why each piece exists, and
what trade-offs were made.

---

## High-level layers

```mermaid
flowchart TB
    subgraph ui [UI Streamlit]
        direction TB
        Login[Login Page]
        Chat[Chat Page]
        Admin[Admin Page]
        Sidebar[Sidebar Components]
        ChatWin[Chat Window]
        Audio[Audio Player]
    end

    subgraph services [Services]
        direction TB
        ChatSvc[ChatService]
        LLMSvc[LLMService]
        TTSSvc[TextToSpeechService]
        STTSvc[SpeechToTextService]
        RAGSvc[RAGService]
        AuthSvc[AuthService]
        Limiter[RateLimiter]
    end

    subgraph data [Data]
        direction TB
        UsersRepo[UserRepository]
        ConvsRepo[ConversationRepository]
        MsgsRepo[MessageRepository]
        Engine[(SQLAlchemy Engine)]
    end

    subgraph external [External]
        OR[OpenRouter LLM]
        GR[Groq Whisper]
        OAI[OpenAI Embeddings]
        ET[edge-tts]
        PC[(Pinecone)]
        DB[(SQLite or Postgres)]
        Sentry[Sentry]
    end

    ui --> services
    services --> data
    data --> Engine
    Engine --> DB

    LLMSvc --> OR
    STTSvc --> GR
    RAGSvc --> OAI
    RAGSvc --> PC
    TTSSvc --> ET
    services -.errors.-> Sentry
```

**Three layers, strict dependency direction**:

- `ui/` -> `services/` -> `db/`
- `ui/` never imports from `db/` directly.
- `services/` never imports from `ui/`.

This makes the services layer testable with no Streamlit context.

---

## Request lifecycle: one chat turn

```mermaid
sequenceDiagram
    autonumber
    participant User
    participant Streamlit as UI Chat Page
    participant ChatSvc as ChatService
    participant Limiter as RateLimiter
    participant RAG as RAGService
    participant LLM as LLMService
    participant DB as Database

    User->>Streamlit: types or speaks message
    Streamlit->>ChatSvc: stream_turn(user_id, conv_id, msg)
    ChatSvc->>Limiter: check(user_id)
    Limiter->>DB: count messages in window
    DB-->>Limiter: N
    Limiter-->>ChatSvc: ok or RateLimitError
    ChatSvc->>DB: persist user message
    ChatSvc->>RAG: context_for(msg) [best-effort]
    RAG-->>ChatSvc: context string or empty
    ChatSvc->>LLM: stream_chat(messages)
    LLM-->>Streamlit: token deltas yielded back through service
    Streamlit-->>User: renders tokens with typing cursor
    ChatSvc->>DB: persist assistant message and touch conversation
```

---

## Data model

```mermaid
erDiagram
    USERS ||--o{ CONVERSATIONS : owns
    CONVERSATIONS ||--o{ MESSAGES : contains

    USERS {
        string id PK
        string username UK
        string email UK
        string hashed_password
        string role
        bool is_active
        datetime created_at
        datetime last_login_at
    }

    CONVERSATIONS {
        string id PK
        string user_id FK
        string title
        string mood
        string language
        text persona
        datetime created_at
        datetime updated_at
    }

    MESSAGES {
        string id PK
        string conversation_id FK
        string role
        text content
        datetime created_at
    }
```

- **UUID primary keys** (string-encoded) for portability across SQLite and Postgres.
- **Cascade deletes**: deleting a user removes their conversations and messages.
- **`ON CONFLICT` not used** — duplicates raise `IntegrityError`, translated to `UserAlreadyExistsError`.

---

## Key design decisions

### 1. Stay on Streamlit (no FastAPI yet)

Streamlit gives us single-file deployment to Streamlit Cloud, free hosting,
and simple iteration. Services are plain Python classes with no Streamlit
imports, so a future FastAPI layer is a drop-in addition rather than a
rewrite.

**Trade-off**: Streamlit is opinionated about reruns and state. We accept
that and isolate per-user state in `session_state`, with the durable state
in SQL.

### 2. SQLAlchemy 2.0 with SQLite default

Works out-of-the-box for solo / small-team. Set `DATABASE_URL=postgresql+psycopg2://...`
to switch — no code change. Alembic migrations work for both.

**SQLite specifics**: we enable `WAL` mode and `foreign_keys=ON` on connect.
`check_same_thread=False` is required because Streamlit reruns scripts on
different threads.

### 3. Repository pattern

Each aggregate root has a thin repository:

- `UserRepository`
- `ConversationRepository`
- `MessageRepository`

Services and UI code never write raw SQL. This gives:

- Easy mocking in tests
- A single place to enforce per-user filtering (security)
- A future swap to a different ORM costs only the repos

### 4. Persistent sliding-window rate limiter

`RateLimiter.check()` simply counts user-role messages from this user in
the last N seconds. Stored alongside the data — no Redis, no in-memory
cache to lose on restart.

**When to upgrade**: switch to Redis with a Lua script when traffic exceeds
a few hundred RPS per pod.

### 5. Streaming everywhere

`LLMService.stream_chat()` yields `str` deltas. `ChatService.stream_turn()`
re-yields them after persisting the user message; the UI calls `st.empty()`
+ `placeholder.markdown()` for the typing-cursor effect.

The final assistant message is persisted in the iterator's `finally` block
so partial responses are still recorded if the user navigates away mid-stream.

### 6. Custom exception hierarchy

Every exception derives from `RupaError` and carries a `user_message`
distinct from its `log_message`. UI layers display `user_message`; loggers
record `log_message` + stack trace. This stops sensitive details from
leaking to end users while keeping them debuggable for operators.

### 7. Structured logging with structlog

`json` format in production goes to stdout, gets picked up by your log
aggregator. `console` format in dev is colourised and human-readable.
Application context (`env`, `app`) is auto-injected on every log line.

### 8. RAG with optional fallback

`RAGService` requires `PINECONE_API_KEY`. The chat page catches missing-RAG
configuration gracefully — chat works without it, just without uploaded
knowledge.

The embedding client prefers `OPENAI_API_KEY` (real OpenAI), falling back
to OpenRouter with a warning, because OpenRouter doesn't reliably proxy
embedding endpoints.

### 9. Per-user TTS files

Each TTS output is written to `data/cache/tts_<session>.mp3` (UUID-based),
not a shared `rupa_speech.mp3`. This was a concurrency bug in the original
prototype.

---

## Observability

| Aspect       | Tool             | Where                                        |
| ------------ | ---------------- | -------------------------------------------- |
| Logs         | structlog (JSON) | `app/logging_setup.py`                       |
| Errors       | Sentry           | `app/observability.py` (auto if DSN set)     |
| Metrics      | -                | (out of scope, add OpenTelemetry if needed)  |
| Tracing      | -                | (Sentry traces ready, sample rate via env)   |
| Health check | Streamlit native | `/_stcore/health` used by Docker healthcheck |

---

## Security model

- **Passwords**: bcrypt (cost factor 12) — never stored in plaintext.
- **Sessions**: Streamlit `session_state`. For an HTTPS deploy behind a
  proxy, the `AUTH_COOKIE_KEY` is reserved for future cookie-based session
  signing.
- **Per-user isolation**: every query touching `Conversation` or `Message`
  uses `get_for_user` / `list_for_user`. Cross-user access is impossible
  without admin role.
- **Admin gate**: `AuthService.require_admin()` raises `PermissionDeniedError`
  if the current user isn't admin. Used by the admin page.
- **Secrets**: never editable in the UI in production. Dev mode shows an
  override panel for convenience.
- **CSRF**: enabled via `enableXsrfProtection = true` in
  `.streamlit/config.toml`.
- **Rate limiting**: per-user, persistent. See above.

---

## Testing pyramid

```
                 /\
                /  \       1 integration test
               /----\      (full chat flow, all externals mocked)
              /      \
             /  unit  \    50+ unit tests
            /----------\   (services, repos, auth, exceptions, utils)
```

Run with:

```bash
pytest -v
```

CI runs the same suite on Python 3.10, 3.11, and 3.12.

---

## What's out of scope (for now)

- Multi-tenancy beyond per-user filtering (no organisations / workspaces)
- Billing / Stripe
- Async background workers (Celery / RQ)
- True WebSocket streaming (Streamlit's model is enough)
- Mobile app
- LLM fine-tuning
