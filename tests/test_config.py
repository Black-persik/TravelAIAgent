import pytest
from pydantic import ValidationError

from tests.conftest import make_settings


def test_database_url_is_built_from_parts_and_escapes_the_password():
    settings = make_settings(postgres_password="p@ss:w/rd", postgres_host="db", postgres_port=6543)
    assert settings.database_url == "postgresql://travel:p%40ss%3Aw%2Frd@db:6543/travel"


def test_secrets_are_masked_in_repr():
    settings = make_settings()
    assert "sk-test-not-a-real-key" not in repr(settings)
    assert "test-db-password" not in repr(settings)


def test_missing_required_secret_fails(monkeypatch):
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    with pytest.raises(ValidationError, match="openrouter_api_key"):
        make_settings(openrouter_api_key=None)


def test_empty_value_falls_back_to_default(monkeypatch):
    # A copied .env.example leaves LANGFUSE_HOST empty: that must mean "use the default".
    monkeypatch.setenv("LANGFUSE_HOST", "")
    assert make_settings().langfuse_host == "https://cloud.langfuse.com"


def test_session_secret_must_be_long():
    with pytest.raises(ValidationError, match="session_secret"):
        make_settings(session_secret="too-short")


def test_tracing_is_off_without_langfuse_keys():
    assert make_settings().tracing_enabled is False
    assert make_settings(
        langfuse_public_key="pk-test", langfuse_secret_key="sk-test"
    ).tracing_enabled
