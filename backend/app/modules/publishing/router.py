"""Publishing endpoints: connect IG, schedule/publish posts."""
import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.config import settings
from app.core.db import get_db
from app.integrations.meta import oauth_url
from app.models.publishing import ScheduledPost, SocialAccount
from app.models.tenant import User
from app.modules.publishing import service
from app.schemas.publishing import ConnectDevIn, PostCreate, PostOut, SocialAccountOut

router = APIRouter(prefix="/publishing", tags=["publishing"])


@router.get("/accounts", response_model=list[SocialAccountOut])
async def list_accounts(
    user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
) -> list[SocialAccount]:
    return list((await db.execute(select(SocialAccount))).scalars().all())


@router.post("/connect/dev", response_model=SocialAccountOut, status_code=201)
async def connect_dev(
    payload: ConnectDevIn,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SocialAccount:
    """Simulated IG connection for demos / dev mode."""
    return await service.connect_dev_account(db, user.tenant_id, payload.account_name)


@router.get("/connect/meta/start")
async def connect_meta_start(user: User = Depends(get_current_user)) -> dict:
    """Return the Facebook Login URL for real IG publishing (needs a Meta app)."""
    if not settings.meta_app_id:
        raise HTTPException(status_code=400, detail="META_APP_ID not configured")
    redirect = f"{settings.cors_origins[0]}/app/publishing"  # set a real callback in prod
    return {"url": oauth_url(settings.meta_app_id, redirect, state=str(user.tenant_id))}


@router.post("/posts", response_model=PostOut, status_code=201)
async def create_post(
    payload: PostCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ScheduledPost:
    post = ScheduledPost(
        tenant_id=user.tenant_id,
        social_account_id=payload.social_account_id,
        trip_id=payload.trip_id,
        creative_asset_id=payload.creative_asset_id,
        image_url=payload.image_url,
        caption=payload.caption,
        scheduled_at=payload.scheduled_at,
        status="scheduled",
    )
    db.add(post)
    await db.flush()
    return post


@router.post("/posts/{post_id}/publish", response_model=PostOut)
async def publish_now(
    post_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ScheduledPost:
    post = await db.get(ScheduledPost, post_id)
    if post is None:
        raise HTTPException(status_code=404, detail="Post not found")
    await service.publish_post(db, post)
    return post


@router.get("/posts", response_model=list[PostOut])
async def list_posts(
    user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
) -> list[ScheduledPost]:
    return list((await db.execute(
        select(ScheduledPost).order_by(ScheduledPost.created_at.desc())
    )).scalars().all())
