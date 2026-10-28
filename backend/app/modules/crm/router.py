"""CRM endpoints: leads pipeline, lead inbox, replies, templates."""
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_current_tenant, get_current_user
from app.core.db import get_db
from app.models.lead import Lead, LeadActivity, Message, MessageTemplate
from app.models.tenant import Tenant, User
from app.modules.crm import service
from app.schemas.crm import (
    ActivityOut,
    InboundIn,
    LeadCreate,
    LeadDetail,
    LeadOut,
    MessageOut,
    ReplyIn,
    StageUpdate,
    TemplateCreate,
    TemplateOut,
)

router = APIRouter(tags=["crm"])


@router.get("/leads", response_model=list[LeadOut])
async def list_leads(
    stage: str | None = None,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[Lead]:
    q = select(Lead).order_by(Lead.created_at.desc())
    if stage:
        q = q.where(Lead.stage == stage)
    return list((await db.execute(q)).scalars().all())


@router.post("/leads", response_model=LeadOut, status_code=201)
async def create_lead(
    payload: LeadCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Lead:
    lead_id = await service.ingest_lead(
        user.tenant_id,
        name=payload.name,
        email=str(payload.email) if payload.email else None,
        phone=payload.phone,
        source=payload.source or "manual",
        trip_id=payload.trip_id,
        notes=payload.notes,
    )
    lead = await db.get(Lead, lead_id)
    if lead is None:
        raise HTTPException(status_code=500, detail="Lead creation failed")
    return lead


@router.get("/leads/{lead_id}", response_model=LeadDetail)
async def get_lead(
    lead_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Lead:
    result = await db.execute(
        select(Lead)
        .where(Lead.id == lead_id)
        .options(selectinload(Lead.messages), selectinload(Lead.activities))
    )
    lead = result.scalar_one_or_none()
    if lead is None:
        raise HTTPException(status_code=404, detail="Lead not found")
    return lead


@router.patch("/leads/{lead_id}/stage", response_model=LeadOut)
async def update_stage(
    lead_id: uuid.UUID,
    payload: StageUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Lead:
    lead = await db.get(Lead, lead_id)
    if lead is None:
        raise HTTPException(status_code=404, detail="Lead not found")
    old = lead.stage
    lead.stage = payload.stage
    db.add(LeadActivity(tenant_id=user.tenant_id, lead_id=lead_id, type="status_change",
                        content=f"{old} → {payload.stage}"))
    return lead


@router.post("/leads/{lead_id}/reply", response_model=MessageOut)
async def reply_to_lead(
    lead_id: uuid.UUID,
    payload: ReplyIn,
    user: User = Depends(get_current_user),
    tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
) -> Message:
    """Agent/human sends an outbound message immediately."""
    lead = await db.get(Lead, lead_id)
    if lead is None:
        raise HTTPException(status_code=404, detail="Lead not found")
    message = Message(tenant_id=user.tenant_id, lead_id=lead_id, channel=payload.channel,
                      direction="outbound", body=payload.body, status="draft", meta={"step": 0})
    db.add(message)
    await db.flush()
    await service.deliver(db, tenant, lead, message)
    return message


@router.post("/leads/{lead_id}/inbound", response_model=LeadOut)
async def simulate_inbound(
    lead_id: uuid.UUID,
    payload: InboundIn,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Lead:
    """Simulate a lead's reply (in production this arrives via a provider webhook)."""
    await service.ingest_inbound(user.tenant_id, lead_id, payload.body, payload.channel)
    lead = await db.get(Lead, lead_id)
    if lead is None:
        raise HTTPException(status_code=404, detail="Lead not found")
    await db.refresh(lead)
    return lead


@router.post("/settings/auto-followup")
async def set_auto_followup(
    enabled: bool,
    tenant: Tenant = Depends(get_current_tenant),
) -> dict:
    """Toggle automatic sending of followups (off = drafts wait in Approvals)."""
    tenant.auto_followup = enabled
    return {"auto_followup": enabled}


@router.get("/templates", response_model=list[TemplateOut])
async def list_templates(
    user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
) -> list[MessageTemplate]:
    return list((await db.execute(select(MessageTemplate).order_by(MessageTemplate.step))).scalars().all())


@router.post("/templates", response_model=TemplateOut, status_code=201)
async def create_template(
    payload: TemplateCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> MessageTemplate:
    tpl = MessageTemplate(tenant_id=user.tenant_id, name=payload.name, channel=payload.channel,
                          subject=payload.subject, body=payload.body, step=payload.step)
    db.add(tpl)
    await db.flush()
    return tpl
