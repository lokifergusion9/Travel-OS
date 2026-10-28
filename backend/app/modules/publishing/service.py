"""Publishing service: connect IG accounts and publish posts (dev or real)."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import decrypt_secret, encrypt_secret
from app.integrations.meta import publish_image
from app.models.publishing import ScheduledPost, SocialAccount


async def connect_dev_account(s: AsyncSession, tenant_id: uuid.UUID, account_name: str) -> SocialAccount:
    """Create a simulated IG connection so the publishing flow is demoable."""
    account = SocialAccount(
        tenant_id=tenant_id, platform="instagram", account_name=account_name,
        ig_user_id=f"dev-{uuid.uuid4().hex[:10]}", access_token_enc=encrypt_secret("dev-token"),
        connected=True, is_dev=True, meta={"note": "dev/simulated account"},
    )
    s.add(account)
    await s.flush()
    return account


async def _default_account(s: AsyncSession) -> SocialAccount | None:
    return (await s.execute(
        select(SocialAccount).where(SocialAccount.connected.is_(True)).limit(1)
    )).scalar_one_or_none()


async def publish_post(s: AsyncSession, post: ScheduledPost) -> None:
    account = None
    if post.social_account_id:
        account = await s.get(SocialAccount, post.social_account_id)
    account = account or await _default_account(s)
    if account is None:
        post.status = "failed"
        post.result = {"detail": "No connected Instagram account"}
        return

    post.status = "publishing"
    token = decrypt_secret(account.access_token_enc) if account.access_token_enc else "dev-"
    result = await publish_image(
        ig_user_id=account.ig_user_id or "", access_token=token,
        image_url=post.image_url or "", caption=post.caption or "", is_dev=account.is_dev,
    )
    post.status = "published" if result.ok else "failed"
    post.published_at = datetime.now(timezone.utc) if result.ok else None
    post.result = {"media_id": result.media_id, "permalink": result.permalink,
                   "mock": result.mock, "detail": result.detail}
