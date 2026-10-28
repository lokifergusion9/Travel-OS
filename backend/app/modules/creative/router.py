"""Creative Studio endpoints: generate (SSE) and list assets."""
import uuid

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.agents.creative import stream_creatives
from app.api.deps import get_current_user
from app.core.db import get_db, tenant_session
from app.core.sse import sse
from app.models.approval import Approval
from app.models.creative import CreativeAsset
from app.models.tenant import User
from app.models.trip import Trip
from app.schemas.trip import CreativeOut, CreativeRequest

router = APIRouter(tags=["creative"])

_VALID_KINDS = {"poster", "caption", "brochure", "reel"}


def _trip_context(trip: Trip) -> dict:
    return {
        "title": trip.title,
        "destination": trip.destination,
        "overview": trip.overview,
        "audience": trip.audience,
        "days": trip.days,
        "itinerary": [
            {
                "day": d.day_number,
                "title": d.title,
                "summary": d.summary,
                "activities": d.activities,
                "stay": d.stay,
                "transport": d.transport,
            }
            for d in trip.days_plan
        ],
        "costing": {
            "currency": trip.costing.currency,
            "per_person": trip.costing.per_person,
        }
        if trip.costing
        else {},
    }


@router.get("/trips/{trip_id}/creatives", response_model=list[CreativeOut])
async def list_creatives(
    trip_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[CreativeAsset]:
    result = await db.execute(
        select(CreativeAsset)
        .where(CreativeAsset.trip_id == trip_id)
        .order_by(CreativeAsset.created_at.desc())
    )
    return list(result.scalars().all())


@router.post("/trips/{trip_id}/creatives/generate")
async def generate_creatives(
    trip_id: uuid.UUID,
    payload: CreativeRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> StreamingResponse:
    result = await db.execute(
        select(Trip)
        .where(Trip.id == trip_id)
        .options(selectinload(Trip.days_plan), selectinload(Trip.costing))
    )
    trip = result.scalar_one_or_none()
    if trip is None:
        raise HTTPException(status_code=404, detail="Trip not found")

    kinds = [k for k in payload.kinds if k in _VALID_KINDS] or ["poster", "caption", "brochure"]
    ctx = _trip_context(trip)
    tenant_id = user.tenant_id
    trip_title = trip.title

    async def event_stream():
        async for ev in stream_creatives(ctx, kinds, str(tenant_id)):
            if ev["type"] == "asset":
                a = ev["asset"]
                asset_id = uuid.uuid4()
                # Persist each asset in its own short tenant-bound transaction.
                async with tenant_session(tenant_id) as s:
                    s.add(
                        CreativeAsset(
                            id=asset_id,
                            tenant_id=tenant_id,
                            trip_id=trip_id,
                            kind=a["kind"],
                            status="pending_review",
                            url=a.get("url"),
                            text_content=a.get("text_content"),
                            meta=a.get("meta", {}),
                        )
                    )
                    s.add(
                        Approval(
                            tenant_id=tenant_id,
                            kind="creative",
                            entity_type="creative_asset",
                            entity_id=asset_id,
                            trip_id=trip_id,
                            title=f"{a['kind'].title()} for {trip_title}",
                            summary=f"Review the generated {a['kind']}.",
                            payload={"kind": a["kind"]},
                        )
                    )
                yield sse({"type": "asset", "id": str(asset_id), "kind": a["kind"],
                           "url": a.get("url"), "text_content": a.get("text_content")})
            elif ev["type"] == "done":
                yield sse({"type": "done", "count": len(ev["assets"])})
            else:
                yield sse(ev)

    return StreamingResponse(event_stream(), media_type="text/event-stream")
