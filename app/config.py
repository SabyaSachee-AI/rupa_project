"""Application configuration via Pydantic Settings.

All runtime configuration is centralised here and loaded from environment
variables (or Streamlit secrets). Each subsystem (LLM, RAG, auth, DB,
observability) has its own nested settings group for clarity.

Usage:
    from app.config import get_settings
    settings = get_settings()
    print(settings.llm.openrouter_api_key.get_secret_value())
"""

from __future__ import annotations

from enum import Enum
from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Environment(str, Enum):
    """Runtime environment."""

    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"
    TEST = "test"


class LLMSettings(BaseSettings):
    """LLM / AI provider configuration."""

    model_config = SettingsConfigDict(env_prefix="", extra="ignore")

    openrouter_api_key: SecretStr = Field(
        default=SecretStr(""),
        validation_alias="OPENROUTER_API_KEY",
        description="OpenRouter API key for chat completions.",
    )
    openrouter_base_url: str = Field(
        default="https://openrouter.ai/api/v1",
        validation_alias="OPENROUTER_BASE_URL",
    )
    chat_model: str = Field(
        default="qwen/qwen-2.5-72b-instruct",
        validation_alias="CHAT_MODEL",
    )
    max_response_tokens: int = Field(
        default=512,
        ge=64,
        le=8192,
        validation_alias="MAX_RESPONSE_TOKENS",
    )

    groq_api_key: SecretStr = Field(
        default=SecretStr(""),
        validation_alias="GROQ_API_KEY",
        description="Groq API key for Whisper STT.",
    )
    stt_model: str = Field(
        default="whisper-large-v3",
        validation_alias="STT_MODEL",
    )

    openai_api_key: SecretStr = Field(
        default=SecretStr(""),
        validation_alias="OPENAI_API_KEY",
        description="OpenAI API key for embeddings. Recommended over OpenRouter.",
    )
    openai_base_url: str = Field(
        default="https://api.openai.com/v1",
        validation_alias="OPENAI_BASE_URL",
    )
    embedding_model: str = Field(
        default="text-embedding-3-small",
        validation_alias="EMBEDDING_MODEL",
    )
    embedding_dimensions: int = Field(
        default=1536,
        ge=64,
        le=4096,
        validation_alias="EMBEDDING_DIMENSIONS",
    )


class RAGSettings(BaseSettings):
    """Vector-database / retrieval configuration."""

    model_config = SettingsConfigDict(env_prefix="", extra="ignore")

    pinecone_api_key: SecretStr = Field(
        default=SecretStr(""),
        validation_alias="PINECONE_API_KEY",
    )
    pinecone_index_name: str = Field(
        default="rupa-knowledge",
        validation_alias="PINECONE_INDEX_NAME",
    )
    chunk_size: int = Field(default=1000, ge=100, le=8000)
    chunk_overlap: int = Field(default=150, ge=0, le=1000)
    top_k: int = Field(default=3, ge=1, le=20)
    upsert_batch_size: int = Field(default=50, ge=1, le=100)


class DatabaseSettings(BaseSettings):
    """Persistent storage configuration."""

    model_config = SettingsConfigDict(env_prefix="", extra="ignore")

    database_url: str = Field(
        default="sqlite:///data/rupa.db",
        validation_alias="DATABASE_URL",
    )
    echo_sql: bool = Field(default=False, validation_alias="DB_ECHO_SQL")
    pool_size: int = Field(default=5, ge=1, le=50, validation_alias="DB_POOL_SIZE")


class AuthSettings(BaseSettings):
    """Authentication configuration."""

    model_config = SettingsConfigDict(env_prefix="", extra="ignore")

    cookie_key: SecretStr = Field(
        default=SecretStr("dev-only-change-me-in-production"),
        validation_alias="AUTH_COOKIE_KEY",
    )
    cookie_name: str = Field(default="rupa_auth", validation_alias="AUTH_COOKIE_NAME")
    cookie_expiry_days: int = Field(
        default=30,
        ge=1,
        le=365,
        validation_alias="AUTH_COOKIE_EXPIRY_DAYS",
    )

    bootstrap_admin_username: str = Field(
        default="admin",
        validation_alias="BOOTSTRAP_ADMIN_USERNAME",
    )
    bootstrap_admin_email: str = Field(
        default="admin@example.com",
        validation_alias="BOOTSTRAP_ADMIN_EMAIL",
    )
    bootstrap_admin_password: SecretStr = Field(
        default=SecretStr("ChangeMe123!"),
        validation_alias="BOOTSTRAP_ADMIN_PASSWORD",
    )


class RateLimitSettings(BaseSettings):
    """Per-user rate limiting."""

    model_config = SettingsConfigDict(env_prefix="", extra="ignore")

    messages: int = Field(default=30, ge=1, le=10_000, validation_alias="RATE_LIMIT_MESSAGES")
    window_seconds: int = Field(
        default=300,
        ge=10,
        le=86_400,
        validation_alias="RATE_LIMIT_WINDOW_SECONDS",
    )


class ObservabilitySettings(BaseSettings):
    """Logging, metrics, and error tracking."""

    model_config = SettingsConfigDict(env_prefix="", extra="ignore")

    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = Field(
        default="INFO",
        validation_alias="LOG_LEVEL",
    )
    log_format: Literal["json", "console"] = Field(
        default="console",
        validation_alias="LOG_FORMAT",
    )

    sentry_dsn: SecretStr = Field(default=SecretStr(""), validation_alias="SENTRY_DSN")
    sentry_traces_sample_rate: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        validation_alias="SENTRY_TRACES_SAMPLE_RATE",
    )


class PathSettings(BaseSettings):
    """Filesystem paths for runtime artifacts."""

    model_config = SettingsConfigDict(env_prefix="", extra="ignore")

    data_dir: Path = Field(default=Path("data"), validation_alias="DATA_DIR")
    cache_dir: Path = Field(default=Path("data/cache"), validation_alias="CACHE_DIR")
    uploads_dir: Path = Field(default=Path("data/uploads"), validation_alias="UPLOADS_DIR")

    @field_validator("data_dir", "cache_dir", "uploads_dir")
    @classmethod
    def _ensure_dir(cls, v: Path) -> Path:
        v.mkdir(parents=True, exist_ok=True)
        return v


class Settings(BaseSettings):
    """Top-level application settings."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    env: Environment = Field(default=Environment.DEVELOPMENT, validation_alias="RUPA_ENV")
    app_host: str = Field(default="0.0.0.0", validation_alias="APP_HOST")  # noqa: S104
    app_port: int = Field(default=8501, ge=1, le=65535, validation_alias="APP_PORT")

    llm: LLMSettings = Field(default_factory=LLMSettings)
    rag: RAGSettings = Field(default_factory=RAGSettings)
    db: DatabaseSettings = Field(default_factory=DatabaseSettings)
    auth: AuthSettings = Field(default_factory=AuthSettings)
    rate_limit: RateLimitSettings = Field(default_factory=RateLimitSettings)
    observability: ObservabilitySettings = Field(default_factory=ObservabilitySettings)
    paths: PathSettings = Field(default_factory=PathSettings)

    @property
    def is_production(self) -> bool:
        return self.env is Environment.PRODUCTION

    @property
    def is_development(self) -> bool:
        return self.env is Environment.DEVELOPMENT

    @property
    def is_test(self) -> bool:
        return self.env is Environment.TEST


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return cached singleton Settings instance.

    Cached so reads are cheap and config is loaded once per process. Tests can
    bust the cache with ``get_settings.cache_clear()``.
    """

    return Settings()
