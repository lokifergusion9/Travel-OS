"""LangGraph itinerary agent.

Flow: research -> plan_days (LLM) -> price -> finalize. The graph streams node
progress for a live "agent at work" UX, then yields a structured draft. The
draft is persisted as ``pending_review`` so a human approves it (HITL) before it
becomes a real trip — the interrupt is realised at the API/approval layer.
"""
from __future__ import annotations

import json
import re
from collections.abc import AsyncIterator
from typing import Any, TypedDict

from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import END, StateGraph

from app.agents.llm.factory import get_chat_model
from app.agents.llm.mock import build_mock_itinerary


class ItineraryInputs(TypedDict, total=False):
    destination: str
    days: int
    audience: str
    season: str
    budget_per_person: int | None


class _State(TypedDict, total=False):
    inputs: ItineraryInputs
    draft: dict[str, Any]


_SYSTEM = (
    "You are an expert travel itinerary planner for a boutique agency. "
    "Given trip parameters, produce a practical, vivid day-by-day plan. "
    "Respond with ONLY valid minified JSON matching this schema: "
    '{"title":str,"destination":str,"days":int,"overview":str,'
    '"itinerary":[{"day":int,"title":str,"summary":str,"activities":[str],'
    '"stay":str,"transport":str}],'
    '"costing":{"currency":str,"per_person":int,'
    '"breakdown":[{"item":str,"amount":int}]}}. No markdown, no prose.'
)


def build_prompt(inputs: ItineraryInputs) -> list[Any]:
    # PARAMS_JSON lets the keyless mock model build a matching response.
    return [
        SystemMessage(content=_SYSTEM),
        HumanMessage(
            content=(
                "Plan this trip.\n"
                f"PARAMS_JSON: {json.dumps(dict(inputs))}"
            )
        ),
    ]


def parse_itinerary(raw: str, inputs: ItineraryInputs) -> dict[str, Any]:
    """Extract JSON from the model output; fall back to a synthesized plan."""
    text = raw.strip()
    fenced = re.search(r"```(?:json)?\s*(\{.*\})\s*```", text, re.DOTALL)
    if fenced:
        text = fenced.group(1)
    else:
        brace = re.search(r"\{.*\}", text, re.DOTALL)
        if brace:
            text = brace.group(0)
    try:
        data = json.loads(text)
        if isinstance(data, dict) and data.get("itinerary"):
            return data
    except json.JSONDecodeError:
        pass
    return build_mock_itinerary(dict(inputs))


# --- Graph nodes ---
async def _research(state: _State) -> dict[str, Any]:
    # Placeholder for future RAG over past itineraries / destination KB (pgvector).
    return {}


async def _plan_days(state: _State) -> dict[str, Any]:
    inputs = state["inputs"]
    model = get_chat_model(temperature=0.6)
    result = await model.ainvoke(build_prompt(inputs))
    content = result.content if isinstance(result.content, str) else str(result.content)
    return {"draft": parse_itinerary(content, inputs)}


async def _price(state: _State) -> dict[str, Any]:
    draft = dict(state.get("draft") or {})
    if not draft.get("costing"):
        draft["costing"] = build_mock_itinerary(dict(state["inputs"]))["costing"]
    return {"draft": draft}


async def _finalize(state: _State) -> dict[str, Any]:
    return {}


def _build_graph():
    g = StateGraph(_State)
    g.add_node("research", _research)
    g.add_node("plan_days", _plan_days)
    g.add_node("price", _price)
    g.add_node("finalize", _finalize)
    g.set_entry_point("research")
    g.add_edge("research", "plan_days")
    g.add_edge("plan_days", "price")
    g.add_edge("price", "finalize")
    g.add_edge("finalize", END)
    return g.compile()


itinerary_graph = _build_graph()

# Human-friendly progress labels per node, for SSE.
_PROGRESS = {
    "research": "Researching the destination…",
    "plan_days": "Drafting the day-by-day plan…",
    "price": "Estimating costs…",
    "finalize": "Finalizing your itinerary…",
}


async def stream_itinerary(
    inputs: ItineraryInputs,
) -> AsyncIterator[dict[str, Any]]:
    """Yield SSE-friendly events: {type: 'progress'|'result', ...}."""
    draft: dict[str, Any] | None = None
    async for update in itinerary_graph.astream(
        {"inputs": inputs}, stream_mode="updates"
    ):
        for node, node_update in update.items():
            if node_update and "draft" in node_update:
                draft = node_update["draft"]
            yield {"type": "progress", "node": node, "message": _PROGRESS.get(node, node)}
    yield {"type": "result", "draft": draft or build_mock_itinerary(dict(inputs))}
