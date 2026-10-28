"""Shared test fixtures. Tests run offline: fake keys, fake models, in-memory checkpoints."""

import json
from collections.abc import Callable, Iterator

import pytest
from fastapi.testclient import TestClient
from langchain_core.language_models import BaseChatModel
from langchain_core.language_models.fake_chat_models import GenericFakeChatModel
from langchain_core.messages import AIMessage
from langgraph.checkpoint.memory import InMemorySaver

from app.api.main import create_app
from app.config import Settings

TEST_USERNAME = "tester"
TEST_PASSWORD = "test-password"


def make_settings(**overrides) -> Settings:
    """Settings with fake values. `_env_file=None` keeps a local .env out of tests."""
    values = {
        "app_env": "local",
        "openrouter_api_key": "sk-test-not-a-real-key",
        "llm_model_fast": "test/fast-model",
        "llm_model_smart": "test/smart-model",
        "langfuse_public_key": None,
        "langfuse_secret_key": None,
        "postgres_user": "travel",
        "postgres_password": "test-db-password",
        "postgres_db": "travel",
        "app_username": TEST_USERNAME,
        "app_password": TEST_PASSWORD,
        "session_secret": "test-session-secret-0123456789abcdef",
    }
    values.update(overrides)
    return Settings(_env_file=None, **values)


def fake_model(*replies: str) -> GenericFakeChatModel:
    """A chat model that returns the given replies in order and streams them word by word."""
    return GenericFakeChatModel(messages=iter([AIMessage(content=r) for r in replies]))


@pytest.fixture
def settings() -> Settings:
    return make_settings()


@pytest.fixture
def client_factory() -> Iterator[Callable[..., TestClient]]:
    """Build a TestClient around the app with a fake model and in-memory checkpoints."""
    clients: list[TestClient] = []

    def build(
        *replies: str,
        llm: BaseChatModel | None = None,
        settings: Settings | None = None,
    ) -> TestClient:
        app = create_app(
            settings=settings or make_settings(),
            llm=llm or fake_model(*replies),
            checkpointer=InMemorySaver(),
        )
        client = TestClient(app)
        client.__enter__()  # runs the app's startup (lifespan)
        clients.append(client)
        return client

    yield build
    for client in clients:
        client.__exit__(None, None, None)


def login(client: TestClient, username: str = TEST_USERNAME, password: str = TEST_PASSWORD):
    return client.post("/api/login", json={"username": username, "password": password})


def parse_sse(body: str) -> list[tuple[str, dict]]:
    """Parse a text/event-stream body into (event, data) pairs."""
    events = []
    for block in body.strip().split("\n\n"):
        event, data = "message", None
        for line in block.splitlines():
            if line.startswith("event:"):
                event = line.removeprefix("event:").strip()
            elif line.startswith("data:"):
                data = json.loads(line.removeprefix("data:").strip())
        if data is not None:
            events.append((event, data))
    return events
