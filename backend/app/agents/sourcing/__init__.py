"""Sourcing Agent (Module 3): hotel & transport vendor outreach drafting."""
from __future__ import annotations

import json
import re
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage

from app.agents.llm.factory import get_chat_model
from app.agents.llm.mock import build_mock_outreach


def _parse_json(raw: str) -> dict[str, Any] | None:
    m = re.search(r"\{.*\}", raw.strip(), re.DOTALL)
    if not m:
        return None
    try:
        data = json.loads(m.group(0))
        return data if isinstance(data, dict) else None
    except json.JSONDecodeError:
        return None


async def draft_outreach(
    *,
    vendor_name: str,
    vendor_type: str,
    destination: str,
    trip_title: str,
    days: int,
    agency: str,
    audience: str | None = None,
) -> dict[str, Any]:
    """Draft a personalized vendor outreach email. Returns {subject, body}."""
    params = {
        "vendor_name": vendor_name, "vendor_type": vendor_type, "destination": destination,
        "trip_title": trip_title, "days": days, "agency": agency, "audience": audience,
    }
    system = (
        "You are a travel agency's sourcing manager writing a B2B outreach email to "
        f"a {vendor_type} vendor to negotiate group rates. Be professional and concise. "
        "Respond with ONLY minified JSON {\"subject\":str,\"body\":str}."
    )
    model = get_chat_model(provider="groq", temperature=0.6)
    result = await model.ainvoke(
        [SystemMessage(content=system),
         HumanMessage(content=f"TASK: outreach\nPARAMS_JSON: {json.dumps(params)}")]
    )
    content = result.content if isinstance(result.content, str) else str(result.content)
    data = _parse_json(content)
    if data and data.get("body"):
        data.setdefault("subject", f"Partnership enquiry — {trip_title}")
        return data
    return build_mock_outreach(params)
