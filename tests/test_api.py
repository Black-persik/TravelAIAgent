from uuid import uuid4

from langchain_core.language_models.fake_chat_models import GenericFakeChatModel

from tests.conftest import login, make_settings, parse_sse


class FailingModel(GenericFakeChatModel):
    """A chat model whose every call fails, e.g. the provider is down."""

    def _generate(self, *args, **kwargs):
        raise RuntimeError("provider is down")

    def _stream(self, *args, **kwargs):
        raise RuntimeError("provider is down")


def chat(client, message: str, thread_id: str | None = None):
    return client.post(
        "/api/chat", json={"thread_id": thread_id or str(uuid4()), "message": message}
    )


def test_health_needs_no_login(client_factory):
    client = client_factory()
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_chat_requires_login(client_factory):
    client = client_factory("unused")
    assert chat(client, "Hi").status_code == 401


def test_wrong_password_is_rejected(client_factory):
    client = client_factory()
    assert login(client, password="wrong").status_code == 401
    assert client.get("/api/me").status_code == 401


def test_login_logout_flow(client_factory):
    client = client_factory()
    assert login(client).status_code == 200
    assert client.get("/api/me").json() == {"username": "tester"}

    assert client.post("/api/logout").status_code == 204
    assert client.get("/api/me").status_code == 401


def test_chat_streams_the_answer_and_saves_history(client_factory):
    client = client_factory("Antalya is warm in November")
    login(client)
    thread_id = str(uuid4())

    response = chat(client, "Somewhere warm in November?", thread_id)

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    events = parse_sse(response.text)
    tokens = [data["text"] for event, data in events if event == "token"]
    assert len(tokens) > 1  # streamed in pieces, not as one block
    assert "".join(tokens) == "Antalya is warm in November"
    assert events[-1] == ("done", {"thread_id": thread_id})

    history = client.get(f"/api/threads/{thread_id}").json()["messages"]
    assert history == [
        {"role": "user", "content": "Somewhere warm in November?"},
        {"role": "assistant", "content": "Antalya is warm in November"},
    ]


def test_model_failure_becomes_an_error_event(client_factory):
    client = client_factory(llm=FailingModel(messages=iter([])))
    login(client)

    events = parse_sse(chat(client, "Hi").text)

    assert events[-1][0] == "error"
    assert "provider is down" not in events[-1][1]["message"]  # no internal details leak


def test_empty_message_is_rejected(client_factory):
    client = client_factory()
    login(client)
    assert chat(client, "").status_code == 422


def test_chat_rate_limit(client_factory):
    client = client_factory("one", "two", settings=make_settings(chat_rate_limit_per_minute=2))
    login(client)

    assert chat(client, "1").status_code == 200
    assert chat(client, "2").status_code == 200
    assert chat(client, "3").status_code == 429


def test_login_rate_limit(client_factory):
    client = client_factory(settings=make_settings(login_rate_limit_per_minute=3))
    for _ in range(3):
        assert login(client, password="wrong").status_code == 401
    assert login(client).status_code == 429  # blocked even with the right password


def test_api_docs_are_disabled_in_production(client_factory):
    client = client_factory(settings=make_settings(app_env="production"))
    assert client.get("/api/docs").status_code == 404
    assert client.get("/api/openapi.json").status_code == 404
