"""Sourcing service: derive needs from a trip, draft vendor outreach, track deals.

Like the other agents, LLM calls run outside any open transaction (short tx ->
agent -> short tx) to preserve the RLS tenant GUC.
"""
from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.sourcing import draft_outreach
from app.core.db import tenant_session
from app.integrations.messaging import send_email
from app.models.approval import Approval
from app.models.sourcing import Deal, Vendor
from app.models.tenant import Tenant
from app.models.trip import Trip


async def generate_sourcing(tenant_id: uuid.UUID, trip_id: uuid.UUID) -> int:
    """Draft outreach to every matching vendor and queue each as an Approval (HITL)."""
    # 1) Gather trip context + candidate vendors (short read tx).
    async with tenant_session(tenant_id) as s:
        trip = await s.get(Trip, trip_id)
        if trip is None:
            return 0
        agency = (await s.get(Tenant, tenant_id)).name
        ctx = {"title": trip.title, "destination": trip.destination,
               "days": trip.days, "audience": trip.audience}
        vendors = (await s.execute(
            select(Vendor).where(Vendor.type.in_(("hotel", "transport")))
        )).scalars().all()
        candidates = [
            {"id": v.id, "name": v.name, "type": v.type, "email": v.contact_email}
            for v in vendors
        ]

    if not candidates:
        return 0

    # 2) Draft outreach per vendor (agent — outside any transaction).
    drafts = []
    for v in candidates:
        d = await draft_outreach(
            vendor_name=v["name"], vendor_type=v["type"], destination=ctx["destination"],
            trip_title=ctx["title"], days=ctx["days"], agency=agency, audience=ctx["audience"],
        )
        drafts.append((v, d))

    # 3) Persist deals + approvals (short write tx).
    async with tenant_session(tenant_id) as s:
        for v, d in drafts:
            deal = Deal(
                tenant_id=tenant_id, trip_id=trip_id, vendor_id=v["id"], kind=v["type"],
                status="requested", outreach_subject=d.get("subject"),
                outreach_body=d.get("body"), sent=False,
            )
            s.add(deal)
            await s.flush()
            s.add(
                Approval(
                    tenant_id=tenant_id, kind="sourcing", entity_type="deal",
                    entity_id=deal.id, trip_id=trip_id,
                    title=f"{v['type'].title()} outreach to {v['name']}",
                    summary=(d.get("body") or "")[:140],
                    payload={"vendor": v["name"], "kind": v["type"]},
                )
            )
    return len(drafts)


async def send_deal_outreach(s: AsyncSession, tenant: Tenant, deal: Deal) -> None:
    """Deliver an approved vendor outreach (console email by default)."""
    vendor = await s.get(Vendor, deal.vendor_id)
    to = vendor.contact_email if vendor else None
    if to:
        await send_email(to, deal.outreach_subject or "Partnership enquiry", deal.outreach_body or "")
    deal.sent = True
