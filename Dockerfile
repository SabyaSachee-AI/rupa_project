# syntax=docker/dockerfile:1.7
# =============================================================================
# Rupa AI - production Docker image
# =============================================================================
# Multi-stage:
#   - builder: installs deps with uv into a venv
#   - runtime: copies venv only, runs as non-root user
# =============================================================================

ARG PYTHON_VERSION=3.12

# -----------------------------------------------------------------------------
# Stage 1: builder
# -----------------------------------------------------------------------------
FROM python:${PYTHON_VERSION}-slim AS builder

ENV PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    VIRTUAL_ENV=/opt/venv \
    PATH="/opt/venv/bin:$PATH"

RUN apt-get update \
    && apt-get install --no-install-recommends -y build-essential curl \
    && rm -rf /var/lib/apt/lists/*

RUN python -m venv $VIRTUAL_ENV

WORKDIR /build

COPY pyproject.toml README.md ./
COPY app/ ./app/

RUN pip install --upgrade pip \
    && pip install ".[postgres]"

# -----------------------------------------------------------------------------
# Stage 2: runtime
# -----------------------------------------------------------------------------
FROM python:${PYTHON_VERSION}-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    VIRTUAL_ENV=/opt/venv \
    PATH="/opt/venv/bin:$PATH" \
    RUPA_ENV=production \
    APP_HOST=0.0.0.0 \
    APP_PORT=8501

RUN apt-get update \
    && apt-get install --no-install-recommends -y curl \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd --system rupa \
    && useradd --system --gid rupa --shell /bin/bash --create-home rupa

COPY --from=builder $VIRTUAL_ENV $VIRTUAL_ENV

WORKDIR /app
COPY --chown=rupa:rupa app/ ./app/
COPY --chown=rupa:rupa alembic/ ./alembic/
COPY --chown=rupa:rupa alembic.ini ./
COPY --chown=rupa:rupa .streamlit/config.toml ./.streamlit/config.toml
COPY --chown=rupa:rupa pyproject.toml README.md LICENSE ./

RUN mkdir -p /app/data/cache /app/data/uploads \
    && chown -R rupa:rupa /app/data

USER rupa

EXPOSE 8501

HEALTHCHECK --interval=30s --timeout=10s --start-period=20s --retries=3 \
    CMD curl --fail --silent --output /dev/null http://localhost:${APP_PORT}/_stcore/health || exit 1

ENTRYPOINT ["streamlit", "run", "app/main.py"]
CMD ["--server.port=8501", "--server.address=0.0.0.0", "--browser.gatherUsageStats=false"]
