"""Trip / itinerary endpoints, including streaming generation (SSE)."""
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

import uuid as _uuid

from app.agents.itinerary import stream_itinerary
from app.api.deps import get_current_user
from app.core.db import get_db, tenant_session
from app.core.sse import sse
from app.models.approval import Approval
from app.models.tenant import User
from app.models.trip import ItineraryDay, Trip, TripCosting
from app.schemas.trip import TripCreate, TripDetail, TripOut

router = APIRouter(prefix="/trips", tags=["trips"])


async def _load_trip(db: AsyncSession, trip_id: uuid.UUID) -> Trip | None:
    result = await db.execute(
        select(Trip)
        .where(Trip.id == trip_id)
        .options(selectinload(Trip.days_plan), selectinload(Trip.costing))
    )
    return result.scalar_one_or_none()


@router.get("", response_model=list[TripOut])
async def list_trips(
    user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
) -> list[Trip]:
    result = await db.execute(select(Trip).order_by(Trip.created_at.desc()))
    return list(result.scalars().all())


@router.get("/{trip_id}", response_model=TripDetail)
async def get_trip(
    trip_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Trip:
    trip = await _load_trip(db, trip_id)
    if trip is None:
        raise HTTPException(status_code=404, detail="Trip not found")
    return trip


@router.post("/generate")
async def generate_trip(
    payload: TripCreate,
    user: User = Depends(get_current_user),
) -> StreamingResponse:
    """Create a trip and stream the itinerary agent's progress (SSE).

    On completion the draft is persisted as ``pending_review`` and an Approval
    row is queued for human sign-off (HITL).
    """
    inputs = {
        "destination": payload.destination,
        "days": payload.days,
        "audience": payload.audience or "travellers",
        "season": payload.season or "",
        "budget_per_person": payload.budget_per_person,
    }
    # Snapshot plain values — the SSE body runs after this request's own session.
    tenant_id = user.tenant_id
    user_id = user.id
    trip_id = _uuid.uuid4()

    async def event_stream():
        yield sse({"type": "trip_created", "trip_id": str(trip_id)})

        # 1) Run the agent (no DB held open across its await points).
        draft: dict | None = None
        async for ev in stream_itinerary(inputs):
            if ev["type"] == "result":
                draft = ev["draft"]
            else:
                yield sse(ev)
        draft = draft or {}

        # 2) Persist everything in one short tenant-bound transaction.
        title = draft.get("title") or f"{payload.days}-Day {payload.destination} Trip"
        costing = draft.get("costing") or {}
        async with tenant_session(tenant_id) as s:
            s.add(
                Trip(
                    id=trip_id,
                    tenant_id=tenant_id,
                    created_by=user_id,
                    title=title,
                    destination=payload.destination,
                    days=payload.days,
                    audience=payload.audience,
                    season=payload.season,
                    budget_per_person=payload.budget_per_person,
                    status="pending_review",
                    overview=draft.get("overview"),
                )
            )
            for d in draft.get("itinerary", []):
                s.add(
                    ItineraryDay(
                        tenant_id=tenant_id,
                        trip_id=trip_id,
                        day_number=int(d.get("day", 0) or 0),
                        title=d.get("title", ""),
                        summary=d.get("summary"),
                        activities=d.get("activities", []),
                        stay=d.get("stay"),
                        transport=d.get("transport"),
                    )
                )
            if costing:
                s.add(
                    TripCosting(
                        tenant_id=tenant_id,
                        trip_id=trip_id,
                        currency=costing.get("currency", "INR"),
                        per_person=costing.get("per_person"),
                        breakdown=costing.get("breakdown", []),
                    )
                )
            s.add(
                Approval(
                    tenant_id=tenant_id,
                    kind="itinerary",
                    entity_type="trip",
                    entity_id=trip_id,
                    trip_id=trip_id,
                    title=title,
                    summary=f"Itinerary for {payload.destination} ({payload.days} days) ready for review.",
                    payload={"days": len(draft.get("itinerary", []))},
                )
            )
        yield sse({"type": "trip", "trip_id": str(trip_id), "draft": draft})

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@router.post("/{trip_id}/approve", response_model=TripOut)
async def approve_trip(
    trip_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Trip:
    trip = await _load_trip(db, trip_id)
    if trip is None:
        raise HTTPException(status_code=404, detail="Trip not found")
    trip.status = "approved"
    # Resolve any pending itinerary approval for this trip.
    result = await db.execute(
        select(Approval).where(
            Approval.entity_id == trip_id,
            Approval.kind == "itinerary",
            Approval.status == "pending",
        )
    )
    from datetime import datetime, timezone

    for appr in result.scalars().all():
        appr.status = "approved"
        appr.decided_by = user.id
        appr.decided_at = datetime.now(timezone.utc)
    return trip
