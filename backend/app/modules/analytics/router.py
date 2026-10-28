"""Analytics: tenant-wide funnel + KPI aggregation for the dashboard."""
from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.db import get_db
from app.models.creative import CreativeAsset
from app.models.lead import LEAD_STAGES, Lead, Message
from app.models.publishing import ScheduledPost
from app.models.sourcing import Deal
from app.models.tenant import User
from app.models.trip import Trip

router = APIRouter(prefix="/analytics", tags=["analytics"])


async def _count(db: AsyncSession, model, *conditions) -> int:
    q = select(func.count()).select_from(model)
    for c in conditions:
        q = q.where(c)
    return int((await db.execute(q)).scalar() or 0)


@router.get("/overview")
async def overview(
    user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
) -> dict:
    # Lead funnel (ordered) + by source.
    stage_rows = dict(
        (s, c) for s, c in (await db.execute(
            select(Lead.stage, func.count()).group_by(Lead.stage)
        )).all()
    )
    funnel = [{"stage": s, "count": int(stage_rows.get(s, 0))} for s in LEAD_STAGES]

    source_rows = (await db.execute(
        select(Lead.source, func.count()).group_by(Lead.source)
    )).all()
    by_source = [{"source": s, "count": int(c)} for s, c in source_rows]

    leads_total = sum(r["count"] for r in funnel)
    won = stage_rows.get("won", 0)

    kpis = {
        "leads_total": leads_total,
        "leads_won": int(won),
        "conversion_rate": round(won / leads_total * 100, 1) if leads_total else 0.0,
        "trips_total": await _count(db, Trip),
        "trips_approved": await _count(db, Trip, Trip.status == "approved"),
        "creatives_total": await _count(db, CreativeAsset),
        "deals_total": await _count(db, Deal),
        "deals_confirmed": await _count(db, Deal, Deal.status == "confirmed"),
        "posts_published": await _count(db, ScheduledPost, ScheduledPost.status == "published"),
        "messages_sent": await _count(db, Message, Message.direction == "outbound", Message.status == "sent"),
        "messages_received": await _count(db, Message, Message.direction == "inbound"),
    }
    return {"kpis": kpis, "funnel": funnel, "by_source": by_source}
