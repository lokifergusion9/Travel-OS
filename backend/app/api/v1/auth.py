"""Authentication & onboarding endpoints.

Tokens are returned in the body (API clients, tests) and the refresh token is
also set as an httpOnly cookie, which is what the SPA uses — so JavaScript
never holds a long-lived credential.
"""
import uuid

import jwt
from fastapi import APIRouter, Cookie, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_tenant, get_current_user, get_user_by_email
from app.core.config import settings
from app.core.db import get_db
from app.core.ratelimit import rate_limit
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.core.utils import random_suffix, slugify
from app.models.tenant import Tenant, User, UserRole
from app.schemas.auth import (
    LoginRequest,
    MeResponse,
    OnboardingUpdate,
    RefreshRequest,
    SignupRequest,
    TenantOut,
    TokenPair,
    UserOut,
)

router = APIRouter(prefix="/auth", tags=["auth"])

_COOKIE_PATH = "/api/v1/auth"


def _issue(response: Response, user: User) -> TokenPair:
    """Mint a token pair for ``user`` and set the refresh cookie."""
    uid, tid, ver = str(user.id), str(user.tenant_id), user.token_version
    pair = TokenPair(
        access_token=create_access_token(uid, tid, ver),
        refresh_token=create_refresh_token(uid, tid, ver),
    )
    response.set_cookie(
        settings.refresh_cookie_name,
        pair.refresh_token,
        max_age=settings.refresh_token_expire_days * 86400,
        path=_COOKIE_PATH,
        httponly=True,
        secure=settings.environment == "production",
        samesite="lax",
    )
    return pair


def _invalid_refresh() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token"
    )


async def _unique_slug(db: AsyncSession, name: str) -> str:
    base = slugify(name)
    slug = base
    while True:
        exists = await db.execute(select(Tenant.id).where(Tenant.slug == slug))
        if exists.first() is None:
            return slug
        slug = f"{base}-{random_suffix()}"


@router.post(
    "/signup",
    response_model=TokenPair,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(rate_limit("signup", 10, 3600))],
)
async def signup(
    payload: SignupRequest, response: Response, db: AsyncSession = Depends(get_db)
) -> TokenPair:
    """Create a new agency workspace (tenant) and its owner user."""
    if await get_user_by_email(db, payload.email):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists",
        )

    tenant = Tenant(name=payload.agency_name, slug=await _unique_slug(db, payload.agency_name))
    db.add(tenant)
    await db.flush()  # populate tenant.id

    user = User(
        tenant_id=tenant.id,
        email=payload.email.lower(),
        hashed_password=hash_password(payload.password),
        full_name=payload.full_name,
        role=UserRole.owner,
    )
    db.add(user)
    await db.flush()
    return _issue(response, user)


@router.post(
    "/login",
    response_model=TokenPair,
    dependencies=[Depends(rate_limit("login", 10, 300))],
)
async def login(
    payload: LoginRequest, response: Response, db: AsyncSession = Depends(get_db)
) -> TokenPair:
    user = await get_user_by_email(db, payload.email)
    if user is None or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password"
        )
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account disabled")
    return _issue(response, user)


@router.post(
    "/refresh",
    response_model=TokenPair,
    dependencies=[Depends(rate_limit("refresh", 60, 300))],
)
async def refresh(
    response: Response,
    payload: RefreshRequest | None = None,
    cookie_token: str | None = Cookie(None, alias=settings.refresh_cookie_name),
    db: AsyncSession = Depends(get_db),
) -> TokenPair:
    """Exchange a refresh token (body or httpOnly cookie) for a fresh pair."""
    token = (payload.refresh_token if payload else None) or cookie_token
    if not token:
        raise _invalid_refresh()
    try:
        claims = decode_token(token)
        if claims.get("type") != "refresh":
            raise ValueError
        user_id = uuid.UUID(claims["sub"])
    except (jwt.PyJWTError, KeyError, ValueError):
        raise _invalid_refresh()

    user = await db.get(User, user_id)
    if user is None or not user.is_active:
        raise _invalid_refresh()
    if claims.get("ver", 0) != user.token_version:  # revoked by logout
        raise _invalid_refresh()
    return _issue(response, user)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(response: Response, user: User = Depends(get_current_user)) -> Response:
    """Revoke every outstanding token for this user (all devices)."""
    user.token_version += 1
    response.delete_cookie(settings.refresh_cookie_name, path=_COOKIE_PATH)
    response.status_code = status.HTTP_204_NO_CONTENT
    return response


@router.get("/me", response_model=MeResponse)
async def me(
    user: User = Depends(get_current_user),
    tenant: Tenant = Depends(get_current_tenant),
) -> MeResponse:
    return MeResponse(user=UserOut.model_validate(user), tenant=TenantOut.model_validate(tenant))


@router.patch("/onboarding", response_model=TenantOut)
async def update_onboarding(
    payload: OnboardingUpdate,
    tenant: Tenant = Depends(get_current_tenant),
) -> TenantOut:
    tenant.onboarding_completed = payload.completed
    return TenantOut.model_validate(tenant)
