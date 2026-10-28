"""CRM service layer: lead creation, first-touch, sending, scheduling.

Important: agent (LLM) calls must NOT run inside an open DB transaction — doing
so drops the RLS tenant GUC (LangChain runs models via a thread executor). So
the ingest helpers do: short tx (write lead) -> agent draft (no tx) -> short tx
(persist message). The background scheduler and message delivery use only
templated text + plain async I/O, which is safe inside a transaction.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.followup import classify_inbound, draft_first_touch
from app.core.config import settings
from app.core.db import tenant_session
from app.integrations.messaging import send as send_message_via
from app.models.approval import Approval
from app.models.lead import Lead, LeadActivity, Message, ScheduledFollowup
from app.models.tenant import Tenant
from app.models.trip import Trip


def _now() -> datetime:
    return datetime.now(timezone.utc)


async def _resolve_interest(s: AsyncSession, trip_id: uuid.UUID | None) -> str:
    if trip_id:
        trip = await s.get(Trip, trip_id)
        if trip:
            return trip.destination
    return "your next trip"


async def schedule_followup(s: AsyncSession, lead: Lead, *, step: int, channel: str) -> None:
    s.add(
        ScheduledFollowup(
            tenant_id=lead.tenant_id,
            lead_id=lead.id,
            run_at=_now() + timedelta(minutes=settings.followup_delay_minutes),
            channel=channel,
            step=step,
            status="scheduled",
        )
    )


async def deliver(s: AsyncSession, tenant: Tenant, lead: Lead, message: Message) -> None:
    """Send a drafted/queued message via the provider, log it, queue next step.

    Uses templated body + plain async HTTP — safe inside a transaction.
    """
    to = lead.email if message.channel == "email" else lead.phone
    if not to:
        message.status = "failed"
        return
    result = await send_message_via(
        message.channel, to=to, subject=message.subject or "", body=message.body
    )
    message.status = "sent" if result.ok else "failed"
    lead.last_contacted_at = _now()
    if lead.stage == "new":
        lead.stage = "contacted"
    s.add(LeadActivity(tenant_id=tenant.id, lead_id=lead.id, type="message_sent",
                       content=message.body[:200],
                       meta={"channel": message.channel, "provider": result.provider}))
    step = int(message.meta.get("step", 0))
    if step < settings.followup_max_steps:
        await schedule_followup(s, lead, step=step + 1, channel=message.channel)


async def _persist_first_touch(
    s: AsyncSession, tenant: Tenant, lead: Lead, draft: dict, channel: str
) -> None:
    message = Message(
        tenant_id=tenant.id, lead_id=lead.id, channel=channel, direction="outbound",
        subject=draft.get("subject"), body=draft["body"], status="draft", meta={"step": 0},
    )
    s.add(message)
    await s.flush()
    if tenant.auto_followup:
        await deliver(s, tenant, lead, message)
    else:
        s.add(
            Approval(
                tenant_id=tenant.id, kind="message", entity_type="message",
                entity_id=message.id, title=f"First-touch {channel} to {lead.name}",
                summary=draft["body"][:140],
                payload={"lead_id": str(lead.id), "channel": channel},
            )
        )


async def ingest_lead(
    tenant_id: uuid.UUID,
    *,
    name: str,
    email: str | None = None,
    phone: str | None = None,
    source: str = "manual",
    trip_id: uuid.UUID | None = None,
    notes: str | None = None,
    source_meta: dict | None = None,
    trigger_first_touch: bool = True,
) -> uuid.UUID:
    """Create a lead and (optionally) its first-touch outreach. Own sessions."""
    lead_id = uuid.uuid4()
    # WhatsApp is the default for phone-only leads (India travel norm).
    channel = "email" if email else "whatsapp"

    # 1) Write the lead, resolve interest (short tx).
    async with tenant_session(tenant_id) as s:
        interest = await _resolve_interest(s, trip_id)
        agency = (await s.get(Tenant, tenant_id)).name
        s.add(
            Lead(id=lead_id, tenant_id=tenant_id, name=name, email=email, phone=phone,
                 source=source, trip_id=trip_id, notes=notes, source_meta=source_meta or {},
                 stage="new")
        )
        s.add(LeadActivity(tenant_id=tenant_id, lead_id=lead_id, type="created",
                           content=f"Lead captured from {source}."))

    if not trigger_first_touch:
        return lead_id

    # 2) Draft the outreach (agent — outside any transaction).
    draft = await draft_first_touch(name=name, interest=interest, agency=agency, channel=channel)

    # 3) Persist the first-touch message / approval (short tx).
    async with tenant_session(tenant_id) as s:
        tenant = await s.get(Tenant, tenant_id)
        lead = await s.get(Lead, lead_id)
        await _persist_first_touch(s, tenant, lead, draft, channel)

    return lead_id


def _reminder_body(name: str, interest: str, step: int) -> str:
    if step >= settings.followup_max_steps:
        return (
            f"Hi {name}, last nudge from us 🙏 — are you still keen on {interest}? "
            "Happy to tweak the plan or budget. Just reply and we'll take it from here."
        )
    return (
        f"Hi {name}! Just following up on your {interest} trip. "
        "Shall I lock in dates and share the final itinerary? Reply and we'll proceed."
    )


async def run_due_followup(
    s: AsyncSession, tenant: Tenant, lead: Lead, followup: ScheduledFollowup
) -> str:
    """Process one due scheduled followup (templated — safe inside a tx)."""
    if lead.stage in ("won", "lost"):
        followup.status = "cancelled"
        return "cancelled"

    interest = await _resolve_interest(s, lead.trip_id)
    message = Message(
        tenant_id=tenant.id, lead_id=lead.id, channel=followup.channel, direction="outbound",
        subject=f"Following up on {interest}" if followup.channel == "email" else None,
        body=_reminder_body(lead.name, interest, followup.step),
        status="draft", meta={"step": followup.step},
    )
    s.add(message)
    await s.flush()

    if tenant.auto_followup:
        await deliver(s, tenant, lead, message)
        outcome = "sent"
    else:
        s.add(
            Approval(
                tenant_id=tenant.id, kind="message", entity_type="message",
                entity_id=message.id, title=f"Follow-up {followup.channel} to {lead.name}",
                summary=message.body[:140],
                payload={"lead_id": str(lead.id), "channel": followup.channel},
            )
        )
        outcome = "queued"
    followup.status = "sent"
    return outcome


async def ingest_inbound(
    tenant_id: uuid.UUID, lead_id: uuid.UUID, body: str, channel: str = "email"
) -> dict:
    """Record an inbound reply, classify intent, advance stage. Returns classification."""
    classified = await classify_inbound(body)  # agent — outside any tx
    async with tenant_session(tenant_id) as s:
        lead = await s.get(Lead, lead_id)
        if lead is None:
            return classified
        s.add(Message(tenant_id=tenant_id, lead_id=lead_id, channel=channel,
                      direction="inbound", body=body, status="received"))
        if lead.stage in ("new", "contacted"):
            lead.stage = "interested"
        s.add(LeadActivity(tenant_id=tenant_id, lead_id=lead_id, type="message_received",
                           content=body[:200], meta=classified))
        pending = await s.execute(
            select(ScheduledFollowup).where(
                ScheduledFollowup.lead_id == lead_id, ScheduledFollowup.status == "scheduled"
            )
        )
        for f in pending.scalars().all():
            f.status = "cancelled"
    return classified


async def send_drafted_message(s: AsyncSession, tenant: Tenant, message: Message) -> None:
    """Deliver an approved draft message (used by the Approval Center)."""
    lead = await s.get(Lead, message.lead_id)
    if lead is not None:
        await deliver(s, tenant, lead, message)


async def ingest_whatsapp_inbound(
    tenant_id: uuid.UUID, from_phone: str, name: str | None, body: str
) -> dict:
    """Route an inbound WhatsApp message to a lead (creating one if new).

    Matches on digits only, so a lead saved as "+91 81680…" still matches the
    bare "9181680…" that WhatsApp delivers (avoids duplicate leads).
    """
    digits = "".join(c for c in from_phone if c.isdigit())
    async with tenant_session(tenant_id) as s:
        existing = (await s.execute(
            select(Lead.id)
            .where(func.regexp_replace(Lead.phone, "[^0-9]", "", "g") == digits)
            .limit(1)
        )).scalar_one_or_none()
        lead_id = existing

    if lead_id is None:
        lead_id = await ingest_lead(
            tenant_id, name=name or from_phone, phone=from_phone, source="whatsapp",
            trigger_first_touch=False,
        )
    return await ingest_inbound(tenant_id, lead_id, body, channel="whatsapp")
