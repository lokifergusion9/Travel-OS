"""Sourcing endpoints: vendors, outreach generation, deals."""
import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.db import get_db
from app.models.sourcing import Deal, Vendor
from app.models.tenant import User
from app.modules.sourcing import service
from app.schemas.sourcing import DealOut, DealUpdate, VendorCreate, VendorOut

router = APIRouter(tags=["sourcing"])


@router.get("/vendors", response_model=list[VendorOut])
async def list_vendors(
    user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
) -> list[Vendor]:
    return list((await db.execute(select(Vendor).order_by(Vendor.created_at.desc()))).scalars().all())


@router.post("/vendors", response_model=VendorOut, status_code=201)
async def create_vendor(
    payload: VendorCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Vendor:
    vendor = Vendor(tenant_id=user.tenant_id, **payload.model_dump())
    db.add(vendor)
    await db.flush()
    return vendor


@router.delete("/vendors/{vendor_id}", status_code=204)
async def delete_vendor(
    vendor_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    vendor = await db.get(Vendor, vendor_id)
    if vendor is not None:
        await db.delete(vendor)


@router.post("/trips/{trip_id}/sourcing/generate")
async def generate_sourcing(
    trip_id: uuid.UUID, user: User = Depends(get_current_user)
) -> dict:
    """Draft outreach to all matching vendors; each waits in the Approval Center."""
    count = await service.generate_sourcing(user.tenant_id, trip_id)
    return {"deals_created": count}


@router.get("/deals", response_model=list[DealOut])
async def list_deals(
    trip_id: uuid.UUID | None = None,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[Deal]:
    q = select(Deal).order_by(Deal.created_at.desc())
    if trip_id:
        q = q.where(Deal.trip_id == trip_id)
    return list((await db.execute(q)).scalars().all())


@router.patch("/deals/{deal_id}", response_model=DealOut)
async def update_deal(
    deal_id: uuid.UUID,
    payload: DealUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Deal:
    deal = await db.get(Deal, deal_id)
    if deal is None:
        raise HTTPException(status_code=404, detail="Deal not found")
    data = payload.model_dump(exclude_none=True)
    for k, v in data.items():
        setattr(deal, k, v)
    return deal
