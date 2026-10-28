"""Deterministic mock chat model + image provider for keyless local dev/tests.

When no GEMINI/GROQ key is configured, agents transparently fall back to these
so the whole pipeline (and the test suite) runs offline. The mock chat model
reads a ``PARAMS_JSON:`` block that agents append to their prompt and returns a
valid, schema-shaped JSON response derived from those params — so output adapts
to the request (destination, days, …) without calling any network service.
"""
from __future__ import annotations

import json
import re
from collections.abc import Iterator
from typing import Any

from langchain_core.callbacks import CallbackManagerForLLMRun
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, AIMessageChunk, BaseMessage
from langchain_core.outputs import ChatGeneration, ChatGenerationChunk, ChatResult

_PARAMS_RE = re.compile(r"PARAMS_JSON:\s*(\{.*\})", re.DOTALL)


def _extract_params(messages: list[BaseMessage]) -> dict[str, Any]:
    for msg in reversed(messages):
        text = msg.content if isinstance(msg.content, str) else str(msg.content)
        m = _PARAMS_RE.search(text)
        if m:
            try:
                return json.loads(m.group(1))
            except json.JSONDecodeError:
                break
    return {}


def build_mock_itinerary(params: dict[str, Any]) -> dict[str, Any]:
    destination = params.get("destination", "the destination")
    days = int(params.get("days", 3) or 3)
    audience = params.get("audience", "travellers")
    budget = params.get("budget_per_person")

    day_plans = []
    for i in range(1, days + 1):
        day_plans.append(
            {
                "day": i,
                "title": f"Day {i} in {destination}",
                "summary": (
                    f"Explore {destination} — guided activities tailored for {audience}."
                ),
                "activities": [
                    "Morning: scenic start & local breakfast",
                    "Afternoon: signature sightseeing / trek leg",
                    "Evening: cultural experience & dinner",
                ],
                "stay": "Curated 3-star property" if i < days else "Departure day",
                "transport": "Private vehicle" if i in (1, days) else "Local transfers",
            }
        )

    per_person = int(budget) if budget else 1500 * days
    return {
        "title": f"{days}-Day {destination} Experience",
        "destination": destination,
        "days": days,
        "overview": (
            f"A {days}-day curated journey through {destination}, designed for "
            f"{audience}. Every step is draft-ready for your review."
        ),
        "itinerary": day_plans,
        "costing": {
            "currency": "INR",
            "per_person": per_person,
            "breakdown": [
                {"item": "Stay", "amount": int(per_person * 0.4)},
                {"item": "Transport", "amount": int(per_person * 0.25)},
                {"item": "Activities & guide", "amount": int(per_person * 0.2)},
                {"item": "Meals & misc", "amount": int(per_person * 0.15)},
            ],
        },
    }


def build_mock_captions(params: dict[str, Any]) -> dict[str, Any]:
    destination = params.get("destination", "your next destination")
    title = params.get("title") or f"{destination} Getaway"
    audience = params.get("audience", "travellers")
    return {
        "instagram": (
            f"✨ {title} ✨\n\n"
            f"Escape to {destination} 🏔️ — handcrafted for {audience}. "
            f"Limited slots, unlimited memories. DM us to book! 📩"
        ),
        "whatsapp": (
            f"Hi! 🌟 Our {title} is now open for bookings. "
            f"A curated {destination} experience for {audience}. "
            f"Reply 'INFO' for the full itinerary & pricing."
        ),
        "hashtags": [
            f"#{str(destination).replace(' ', '')}",
            "#TravelOS",
            "#Wanderlust",
            "#TripGoals",
            "#IncredibleIndia",
        ],
    }


def build_mock_first_touch(params: dict[str, Any]) -> dict[str, Any]:
    name = params.get("name") or "there"
    interest = params.get("interest") or params.get("destination") or "your next trip"
    agency = params.get("agency") or "our travel agency"
    channel = params.get("channel", "email")
    body = (
        f"Hi {name}! 👋 Thanks for your interest in {interest}. "
        f"This is {agency}. We'd love to craft the perfect trip for you — "
        "do you have preferred dates and a group size in mind? "
        "Reply here and we'll share a tailored itinerary & pricing."
    )
    subject = f"Let's plan {interest}!" if channel == "email" else None
    return {"subject": subject, "body": body}


def build_mock_classification(params: dict[str, Any]) -> dict[str, Any]:
    text = str(params.get("message", "")).lower()
    if any(w in text for w in ("price", "cost", "budget", "how much", "rate")):
        intent, suggestion = "price", "Share the itinerary with per-person pricing."
    elif any(w in text for w in ("date", "when", "available", "month", "weekend")):
        intent, suggestion = "dates", "Confirm available departure dates and hold a slot."
    elif any(w in text for w in ("not", "later", "busy", "maybe", "next time")):
        intent, suggestion = "not_now", "Schedule a gentle follow-up in a few days."
    elif any(w in text for w in ("yes", "interested", "book", "confirm", "sounds good", "great")):
        intent, suggestion = "interested", "Move to proposal and send the booking link."
    else:
        intent, suggestion = "other", "Reply to clarify their needs."
    return {"intent": intent, "suggestion": suggestion}


def build_mock_outreach(params: dict[str, Any]) -> dict[str, Any]:
    vendor = params.get("vendor_name") or "team"
    vtype = params.get("vendor_type", "hotel")
    destination = params.get("destination", "the destination")
    trip = params.get("trip_title") or f"{destination} trip"
    days = params.get("days", "")
    agency = params.get("agency", "our travel agency")
    pax = params.get("audience") or "a group"
    need = "rooms" if vtype == "hotel" else "vehicles/transfers"
    subject = f"Partnership enquiry — {trip}"
    body = (
        f"Hi {vendor},\n\n"
        f"This is {agency}. We're organising '{trip}' ({days} days in {destination}) "
        f"for {pax} and would love to work with you for {need}.\n\n"
        "Could you share your best group rates, availability, and any package deals? "
        "We run trips here regularly and are looking for a reliable long-term partner.\n\n"
        "Looking forward to your quote.\n\nWarm regards"
    )
    return {"subject": subject, "body": body}


def build_mock_reel(params: dict[str, Any]) -> dict[str, Any]:
    destination = params.get("destination", "the destination")
    title = params.get("title") or f"{destination} Reel"
    audience = params.get("audience") or "travellers"
    return {
        "title": title,
        "hook": f"POV: you finally booked {destination} 🌄",
        "music_vibe": "uplifting indie travel beat",
        "scenes": [
            {"order": 1, "text": f"Sunrise over {destination} 🌅", "visual": "wide landscape pan", "seconds": 3},
            {"order": 2, "text": "Adventures all day ⛰️", "visual": "fast activity cuts", "seconds": 3},
            {"order": 3, "text": f"Made for {audience} ✨", "visual": "smiling group", "seconds": 3},
            {"order": 4, "text": "Limited slots — DM to book 📩", "visual": "logo + price card", "seconds": 3},
        ],
        "cta": "DM 'TRIP' to grab your spot!",
    }


def _has_task(messages: list[BaseMessage], task: str) -> bool:
    for msg in messages:
        text = msg.content if isinstance(msg.content, str) else str(msg.content)
        if f"TASK: {task}" in text:
            return True
    return False


class MockChatModel(BaseChatModel):
    """Deterministic JSON responses built from a PARAMS_JSON block.

    Branches on a ``TASK:`` marker so one mock serves multiple agents
    (itinerary by default, captions when ``TASK: captions`` is present).
    """

    @property
    def _llm_type(self) -> str:
        return "mock-travelos"

    def _build_text(self, messages: list[BaseMessage]) -> str:
        params = _extract_params(messages)
        if _has_task(messages, "captions"):
            return json.dumps(build_mock_captions(params), ensure_ascii=False)
        if _has_task(messages, "first_touch"):
            return json.dumps(build_mock_first_touch(params), ensure_ascii=False)
        if _has_task(messages, "classify"):
            return json.dumps(build_mock_classification(params), ensure_ascii=False)
        if _has_task(messages, "outreach"):
            return json.dumps(build_mock_outreach(params), ensure_ascii=False)
        if _has_task(messages, "reel"):
            return json.dumps(build_mock_reel(params), ensure_ascii=False)
        return json.dumps(build_mock_itinerary(params), ensure_ascii=False)

    def _generate(
        self,
        messages: list[BaseMessage],
        stop: list[str] | None = None,
        run_manager: CallbackManagerForLLMRun | None = None,
        **kwargs: Any,
    ) -> ChatResult:
        text = self._build_text(messages)
        return ChatResult(generations=[ChatGeneration(message=AIMessage(content=text))])

    def _stream(
        self,
        messages: list[BaseMessage],
        stop: list[str] | None = None,
        run_manager: CallbackManagerForLLMRun | None = None,
        **kwargs: Any,
    ) -> Iterator[ChatGenerationChunk]:
        text = self._build_text(messages)
        # Emit in word chunks so the UI sees a realistic stream.
        for token in re.findall(r"\S+\s*", text):
            yield ChatGenerationChunk(message=AIMessageChunk(content=token))
