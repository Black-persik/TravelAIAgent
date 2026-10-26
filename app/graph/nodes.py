"""Graph nodes. Each node takes the current TripState and returns the fields it updates."""

from collections.abc import Awaitable, Callable

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import SystemMessage

from app.graph.prompts import SYSTEM_PROMPT
from app.graph.state import TripState

Node = Callable[[TripState], Awaitable[dict]]


def make_respond_node(llm: BaseChatModel) -> Node:
    """Build the node that answers the traveller.

    The model is passed in (not created inside), so tests can use a fake model.
    """

    async def respond(state: TripState) -> dict:
        messages = [SystemMessage(content=SYSTEM_PROMPT), *state["messages"]]
        reply = await llm.ainvoke(messages)
        return {"messages": [reply]}

    return respond
