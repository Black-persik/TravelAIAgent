"""Application settings.

All configuration is read here, from environment variables (in Docker) or a local
`.env` file (when running without Docker). Nothing else in the app reads
`os.environ` directly. Secrets are `SecretStr`, so they are masked in logs and reprs.
"""

from functools import lru_cache
from typing import Literal
from urllib.parse import quote

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        # An empty value (`LANGFUSE_HOST=`) means "not set", so the default applies.
        env_ignore_empty=True,
    )

    # "local" relaxes cookie security for http://localhost and enables API docs.
    app_env: Literal["local", "production"] = "production"

    # LLM provider (OpenRouter, OpenAI-compatible API)
    openrouter_api_key: SecretStr
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    llm_model_fast: str  # cheap model for extraction and classification (used from stage 3)
    llm_model_smart: str  # strong model for planning and explanations

    # Tracing (optional: tracing is off when the keys are empty)
    langfuse_public_key: str | None = None
    langfuse_secret_key: SecretStr | None = None
    langfuse_host: str = "https://cloud.langfuse.com"

    # Database: the URL is assembled from parts, so the password lives in one place
    postgres_user: str
    postgres_password: SecretStr
    postgres_db: str
    postgres_host: str = "postgres"
    postgres_port: int = 5432

    # Access to the web UI
    app_username: str
    app_password: SecretStr
    session_secret: SecretStr = Field(min_length=32)

    # Requests per user (chat) or per IP (login) per minute
    chat_rate_limit_per_minute: int = 20
    login_rate_limit_per_minute: int = 5

    @property
    def database_url(self) -> str:
        user = quote(self.postgres_user, safe="")
        password = quote(self.postgres_password.get_secret_value(), safe="")
        db = quote(self.postgres_db, safe="")
        return f"postgresql://{user}:{password}@{self.postgres_host}:{self.postgres_port}/{db}"

    @property
    def is_local(self) -> bool:
        return self.app_env == "local"

    @property
    def tracing_enabled(self) -> bool:
        return bool(self.langfuse_public_key and self.langfuse_secret_key)


@lru_cache
def get_settings() -> Settings:
    return Settings()
