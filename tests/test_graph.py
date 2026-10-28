from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.checkpoint.memory import InMemorySaver

from app.graph.builder import build_graph
from app.graph.nodes import make_respond_node
from app.graph.prompts import SYSTEM_PROMPT
from tests.conftest import fake_model


class RecordingModel:
    """Minimal stand-in for a chat model that records what it was called with."""

    def __init__(self, reply: str) -> None:
        self.calls: list[list] = []
        self._model = fake_model(reply)

    async def ainvoke(self, messages, *args, **kwargs):
        self.calls.append(messages)
        return await self._model.ainvoke(messages, *args, **kwargs)


async def test_respond_node_adds_system_prompt_and_returns_only_the_reply():
    model = RecordingModel("Try Antalya in November.")
    node = make_respond_node(model)

    update = await node({"messages": [HumanMessage(content="Somewhere warm?")]})

    sent = model.calls[0]
    assert isinstance(sent[0], SystemMessage)
    assert sent[0].content == SYSTEM_PROMPT
    assert sent[1].content == "Somewhere warm?"
    assert len(update["messages"]) == 1
    assert update["messages"][0].content == "Try Antalya in November."


async def test_graph_remembers_the_conversation_per_thread():
    graph = build_graph(
        fake_model("First answer", "Second answer", "Other thread"), InMemorySaver()
    )
    thread_a = {"configurable": {"thread_id": "a"}}
    thread_b = {"configurable": {"thread_id": "b"}}

    await graph.ainvoke({"messages": [HumanMessage(content="Hi")]}, thread_a)
    await graph.ainvoke({"messages": [HumanMessage(content="Two days later?")]}, thread_a)
    await graph.ainvoke({"messages": [HumanMessage(content="Hello")]}, thread_b)

    history_a = (await graph.aget_state(thread_a)).values["messages"]
    history_b = (await graph.aget_state(thread_b)).values["messages"]
    assert [m.content for m in history_a] == [
        "Hi",
        "First answer",
        "Two days later?",
        "Second answer",
    ]
    assert [m.content for m in history_b] == ["Hello", "Other thread"]
