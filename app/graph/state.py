"""TripState: the single source of truth for a trip.

Stage 1 keeps only the conversation. The structured fields from docs/ARCHITECTURE.md
(profile, assumptions, weights, destinations, options, selection, cart, stage) are
added in stage 3, when the nodes that fill them exist.
"""

from typing import Annotated, TypedDict

from langchain_core.messages import AnyMessage
from langgraph.graph.message import add_messages


class TripState(TypedDict):
    # `add_messages` is a reducer: a node returns only its new messages and LangGraph
    # appends them to the history instead of replacing it.
    messages: Annotated[list[AnyMessage], add_messages]
