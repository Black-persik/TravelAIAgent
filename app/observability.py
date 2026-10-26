"""Langfuse tracing. Disabled automatically when the Langfuse keys are not set."""

from typing import Any

from langfuse import Langfuse
from langfuse.langchain import CallbackHandler

from app.config import Settings


def build_langfuse(settings: Settings) -> Langfuse | None:
    if not settings.tracing_enabled:
        return None
    assert settings.langfuse_secret_key is not None  # guaranteed by tracing_enabled
    return Langfuse(
        public_key=settings.langfuse_public_key,
        secret_key=settings.langfuse_secret_key.get_secret_value(),
        base_url=settings.langfuse_host,
        environment=settings.app_env,
    )


def tracing_config(settings: Settings, *, session_id: str, user_id: str) -> dict[str, Any]:
    """Callbacks and metadata to merge into a LangGraph run config.

    Langfuse groups all turns of one conversation by `langfuse_session_id`.
    """
    if not settings.tracing_enabled:
        return {}
    return {
        "callbacks": [CallbackHandler(public_key=settings.langfuse_public_key)],
        "metadata": {"langfuse_session_id": session_id, "langfuse_user_id": user_id},
    }
