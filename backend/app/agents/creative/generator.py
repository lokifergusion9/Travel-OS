"""Creative generation: poster (image model), captions (LLM), brochure (PDF).

Exposes ``stream_creatives`` which yields progress events and finally asset
descriptors. The API layer persists those as CreativeAssets + Approval rows so
every creative is reviewed before it can be published (HITL).
"""
from __future__ import annotations

import json
import re
from collections.abc import AsyncIterator
from typing import Any

from fpdf import FPDF
from langchain_core.messages import HumanMessage, SystemMessage

from app.agents.llm.factory import get_chat_model, get_image_provider
from app.agents.llm.mock import build_mock_captions, build_mock_reel
from app.integrations.storage import get_storage

KINDS = ("poster", "caption", "brochure", "reel")


def _poster_prompt(ctx: dict[str, Any]) -> str:
    return (
        f"Vibrant cinematic travel poster for '{ctx.get('title')}'. "
        f"Destination: {ctx.get('destination')}. "
        f"Audience: {ctx.get('audience') or 'travellers'}. "
        "Bold typography space at top, dramatic landscape, warm sunset palette, "
        "high detail, marketing-ready."
    )


def _reel_messages(ctx: dict[str, Any]) -> list[Any]:
    system = (
        "You are a short-form video producer for a travel agency. Draft a punchy "
        "Instagram Reel storyboard. Respond with ONLY minified JSON "
        '{"title":str,"hook":str,"music_vibe":str,'
        '"scenes":[{"order":int,"text":str,"visual":str,"seconds":int}],"cta":str}.'
    )
    params = {"title": ctx.get("title"), "destination": ctx.get("destination"),
              "audience": ctx.get("audience")}
    return [
        SystemMessage(content=system),
        HumanMessage(content=f"TASK: reel\nPARAMS_JSON: {json.dumps(params)}"),
    ]


def _parse_reel(raw: str, ctx: dict[str, Any]) -> dict[str, Any]:
    m = re.search(r"\{.*\}", raw.strip(), re.DOTALL)
    if m:
        try:
            data = json.loads(m.group(0))
            if isinstance(data, dict) and data.get("scenes"):
                return data
        except json.JSONDecodeError:
            pass
    return build_mock_reel(ctx)


def _caption_messages(ctx: dict[str, Any]) -> list[Any]:
    system = (
        "You are a social media copywriter for a travel agency. Write punchy, "
        "emoji-rich copy. Respond with ONLY valid minified JSON: "
        '{"instagram":str,"whatsapp":str,"hashtags":[str]}.'
    )
    params = {
        "title": ctx.get("title"),
        "destination": ctx.get("destination"),
        "audience": ctx.get("audience"),
    }
    return [
        SystemMessage(content=system),
        HumanMessage(
            content=f"TASK: captions\nWrite captions.\nPARAMS_JSON: {json.dumps(params)}"
        ),
    ]


def _parse_captions(raw: str, ctx: dict[str, Any]) -> dict[str, Any]:
    text = raw.strip()
    m = re.search(r"\{.*\}", text, re.DOTALL)
    if m:
        try:
            data = json.loads(m.group(0))
            if isinstance(data, dict) and data.get("instagram"):
                return data
        except json.JSONDecodeError:
            pass
    return build_mock_captions(ctx)


def _latin1(text: str) -> str:
    """fpdf2 core fonts are latin-1; drop unsupported chars (e.g. emoji)."""
    return text.encode("latin-1", "replace").decode("latin-1")


def _build_brochure_pdf(ctx: dict[str, Any]) -> bytes:
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    def para(text: str, size: int, style: str = "", rgb: tuple[int, int, int] = (0, 0, 0)) -> None:
        # new_x/new_y reset the cursor so consecutive full-width cells stack.
        pdf.set_font("Helvetica", style, size)
        pdf.set_text_color(*rgb)
        pdf.multi_cell(0, size * 0.5 + 2, _latin1(text), new_x="LMARGIN", new_y="NEXT")

    para(str(ctx.get("title", "Trip")), 22, "B")
    para(f"{ctx.get('destination', '')}  -  {ctx.get('days', '')} days", 12, "", (90, 90, 90))
    pdf.ln(2)
    if ctx.get("overview"):
        para(str(ctx["overview"]), 11, "I")
        pdf.ln(2)

    for day in ctx.get("itinerary", []):
        para(f"Day {day.get('day')}: {day.get('title', '')}", 13, "B")
        if day.get("summary"):
            para(str(day["summary"]), 11)
        for act in day.get("activities", []):
            para(f"  - {act}", 11)
        meta = " | ".join(filter(None, [day.get("stay"), day.get("transport")]))
        if meta:
            para(meta, 10, "", (110, 110, 110))
        pdf.ln(1)

    costing = ctx.get("costing") or {}
    if costing.get("per_person"):
        pdf.ln(2)
        para(f"Price: {costing.get('currency', 'INR')} {costing['per_person']} / person", 13, "B")

    return bytes(pdf.output())


async def stream_creatives(
    ctx: dict[str, Any],
    kinds: list[str],
    tenant_id: str,
) -> AsyncIterator[dict[str, Any]]:
    """Yield {type:'progress'|'asset'|'done'} events; persists files via storage."""
    storage = get_storage()
    assets: list[dict[str, Any]] = []

    if "poster" in kinds:
        yield {"type": "progress", "kind": "poster", "message": "Designing your poster…"}
        prompt = _poster_prompt(ctx)
        try:
            img = await get_image_provider().generate(prompt, width=1024, height=1280)
        except Exception:
            # Never hard-fail the creative flow if the image API is down/paywalled.
            from app.agents.llm.images import MockImageProvider

            img = await MockImageProvider().generate(prompt, width=1024, height=1280)
        url = storage.save(tenant_id, img.data, img.ext)
        asset = {"kind": "poster", "url": url, "text_content": None,
                 "meta": {"prompt": _poster_prompt(ctx), "content_type": img.content_type}}
        assets.append(asset)
        yield {"type": "asset", "asset": asset}

    if "caption" in kinds:
        yield {"type": "progress", "kind": "caption", "message": "Writing captions…"}
        model = get_chat_model(provider="groq", temperature=0.8)
        result = await model.ainvoke(_caption_messages(ctx))
        content = result.content if isinstance(result.content, str) else str(result.content)
        caps = _parse_captions(content, ctx)
        text = (
            f"📸 Instagram:\n{caps.get('instagram', '')}\n\n"
            f"💬 WhatsApp:\n{caps.get('whatsapp', '')}\n\n"
            f"{' '.join(caps.get('hashtags', []))}"
        )
        asset = {"kind": "caption", "url": None, "text_content": text, "meta": caps}
        assets.append(asset)
        yield {"type": "asset", "asset": asset}

    if "brochure" in kinds:
        yield {"type": "progress", "kind": "brochure", "message": "Laying out the brochure…"}
        pdf_bytes = _build_brochure_pdf(ctx)
        url = storage.save(tenant_id, pdf_bytes, "pdf")
        asset = {"kind": "brochure", "url": url, "text_content": None,
                 "meta": {"content_type": "application/pdf"}}
        assets.append(asset)
        yield {"type": "asset", "asset": asset}

    if "reel" in kinds:
        yield {"type": "progress", "kind": "reel", "message": "Storyboarding a reel…"}
        # A vertical cover frame + a scene-by-scene storyboard (client-rendered).
        prompt = f"Vertical 9:16 travel reel cover for {ctx.get('destination')}, cinematic, bold text space"
        try:
            img = await get_image_provider().generate(prompt, width=1024, height=1820)
        except Exception:
            from app.agents.llm.images import MockImageProvider

            img = await MockImageProvider().generate(prompt, width=1024, height=1820)
        cover_url = storage.save(tenant_id, img.data, img.ext)
        model = get_chat_model(temperature=0.8)
        result = await model.ainvoke(_reel_messages(ctx))
        content = result.content if isinstance(result.content, str) else str(result.content)
        storyboard = _parse_reel(content, ctx)
        asset = {"kind": "reel", "url": cover_url, "text_content": json.dumps(storyboard),
                 "meta": storyboard}
        assets.append(asset)
        yield {"type": "asset", "asset": asset}

    yield {"type": "done", "assets": assets}
