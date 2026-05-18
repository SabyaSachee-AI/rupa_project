"""Tests for the Pydantic Settings configuration layer."""

from __future__ import annotations

import pytest

from app.config import Environment, get_settings


@pytest.mark.unit
class TestSettings:
    def test_environment_defaults_to_test_in_test_suite(self) -> None:
        settings = get_settings()
        assert settings.env is Environment.TEST

    def test_llm_keys_loaded_from_env(self) -> None:
        settings = get_settings()
        assert settings.llm.openrouter_api_key.get_secret_value() == "test-or-key"
        assert settings.llm.groq_api_key.get_secret_value() == "test-groq-key"
        assert settings.llm.openai_api_key.get_secret_value() == "test-openai-key"

    def test_is_production_flag(self) -> None:
        settings = get_settings()
        assert settings.is_production is False
        assert settings.is_test is True

    def test_db_url_in_memory_sqlite(self) -> None:
        settings = get_settings()
        assert "sqlite" in settings.db.database_url

    def test_rag_defaults_sensible(self) -> None:
        settings = get_settings()
        assert settings.rag.top_k == 3
        assert settings.rag.chunk_size == 1000
        assert settings.rag.chunk_overlap == 150
        assert settings.rag.upsert_batch_size == 50

    def test_settings_singleton(self) -> None:
        a = get_settings()
        b = get_settings()
        assert a is b
