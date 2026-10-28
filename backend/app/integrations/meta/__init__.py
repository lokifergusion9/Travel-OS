"""Instagram Graph API publishing (Meta).

Two paths:
  - dev (no real Meta app): simulate publishing so the whole flow is demoable.
  - real: Content Publishing API — create a media container, then publish it.
    Requires a Business/Creator IG account linked to a Facebook Page and a
    long-lived token with instagram_content_publish (App Review for prod).
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass

import httpx

GRAPH = "https://graph.facebook.com/v21.0"


@dataclass
class PublishResult:
    ok: bool
    media_id: str | None
    permalink: str | None
    detail: str = ""
    mock: bool = False


async def publish_image(
    *, ig_user_id: str, access_token: str, image_url: str, caption: str, is_dev: bool
) -> PublishResult:
    """Publish a single image to an IG account (or simulate in dev)."""
    if is_dev or not ig_user_id or access_token.startswith("dev-"):
        fake = uuid.uuid4().hex[:16]
        return PublishResult(True, media_id=fake, permalink=f"https://instagram.com/p/{fake}",
                             detail="dev mock publish", mock=True)
    try:
        async with httpx.AsyncClient(timeout=60) as client:
            create = await client.post(
                f"{GRAPH}/{ig_user_id}/media",
                params={"image_url": image_url, "caption": caption, "access_token": access_token},
            )
            create.raise_for_status()
            creation_id = create.json()["id"]
            pub = await client.post(
                f"{GRAPH}/{ig_user_id}/media_publish",
                params={"creation_id": creation_id, "access_token": access_token},
            )
            pub.raise_for_status()
            media_id = pub.json()["id"]
            info = await client.get(
                f"{GRAPH}/{media_id}",
                params={"fields": "permalink", "access_token": access_token},
            )
            permalink = info.json().get("permalink") if info.is_success else None
        return PublishResult(True, media_id=media_id, permalink=permalink)
    except httpx.HTTPError as e:
        return PublishResult(False, media_id=None, permalink=None, detail=str(e)[:200])


def oauth_url(app_id: str, redirect_uri: str, state: str) -> str:
    """Facebook Login dialog URL for IG publishing permissions."""
    scopes = "instagram_basic,instagram_content_publish,pages_show_list,business_management"
    return (
        "https://www.facebook.com/v21.0/dialog/oauth"
        f"?client_id={app_id}&redirect_uri={redirect_uri}&state={state}"
        f"&scope={scopes}&response_type=code"
    )
