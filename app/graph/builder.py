"""Graph assembly. Stage 1 is a single node: START -> respond -> END."""

from langchain_core.language_models import BaseChatModel
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph

from app.graph.nodes import make_respond_node
from app.graph.state import TripState


def build_graph(llm: BaseChatModel, checkpointer: BaseCheckpointSaver) -> CompiledStateGraph:
    """Compile the agent graph.

    The checkpointer saves TripState after every step, keyed by `thread_id`, so a
    conversation continues where it stopped, even after a server restart.
    """
    builder = StateGraph(TripState)
    builder.add_node("respond", make_respond_node(llm))
    builder.add_edge(START, "respond")
    builder.add_edge("respond", END)
    return builder.compile(checkpointer=checkpointer)
