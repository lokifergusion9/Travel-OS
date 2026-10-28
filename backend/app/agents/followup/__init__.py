"""Lead / Followup Agent (Module 5).

Drafts first-touch outreach for new leads and classifies inbound replies so the
CRM can suggest the next action. Mock-friendly (works with no API key); uses the
fast Groq model when a key is configured.
"""
from __future__ import annotations

import json
import re
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage

from app.agents.llm.factory import get_chat_model
from app.agents.llm.mock import build_mock_classification, build_mock_first_touch


def _parse_json(raw: str) -> dict[str, Any] | None:
    m = re.search(r"\{.*\}", raw.strip(), re.DOTALL)
    if not m:
        return None
    try:
        data = json.loads(m.group(0))
        return data if isinstance(data, dict) else None
    except json.JSONDecodeError:
        return None


async def draft_first_touch(
    *, name: str, interest: str, agency: str, channel: str = "email"
) -> dict[str, Any]:
    """Return {'subject': str|None, 'body': str} for the first outreach."""
    params = {"name": name, "interest": interest, "agency": agency, "channel": channel}
    system = (
        "You are a warm, concise travel-agency sales rep writing a first outreach "
        "to a new lead. Respond with ONLY minified JSON {\"subject\":str|null,"
        "\"body\":str}. Keep it friendly, ask for dates & group size."
    )
    model = get_chat_model(provider="groq", temperature=0.7)
    result = await model.ainvoke(
        [SystemMessage(content=system),
         HumanMessage(content=f"TASK: first_touch\nPARAMS_JSON: {json.dumps(params)}")]
    )
    content = result.content if isinstance(result.content, str) else str(result.content)
    data = _parse_json(content)
    if data and data.get("body"):
        data.setdefault("subject", None)
        return data
    return build_mock_first_touch(params)


async def classify_inbound(text: str) -> dict[str, Any]:
    """Return {'intent': str, 'suggestion': str} for an inbound reply."""
    system = (
        "You classify a lead's reply for a travel agency. Intents: interested, "
        "price, dates, not_now, other. Respond with ONLY minified JSON "
        "{\"intent\":str,\"suggestion\":str}."
    )
    model = get_chat_model(provider="groq", temperature=0.2)
    result = await model.ainvoke(
        [SystemMessage(content=system),
         HumanMessage(content=f"TASK: classify\nPARAMS_JSON: {json.dumps({'message': text})}")]
    )
    content = result.content if isinstance(result.content, str) else str(result.content)
    data = _parse_json(content)
    if data and data.get("intent"):
        data.setdefault("suggestion", "")
        return data
    return build_mock_classification({"message": text})
