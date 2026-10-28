"""Shared FastAPI dependencies: DB session, current user, tenant RLS binding."""
import uuid

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db, set_tenant
from app.core.security import decode_token
from app.models.tenant import Tenant, User

bearer_scheme = HTTPBearer(auto_error=True)

_CREDENTIALS_EXC = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Could not validate credentials",
    headers={"WWW-Authenticate": "Bearer"},
)


async def get_current_user(
    creds: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Validate the access token, load the user, and bind the request to the
    user's tenant for Row-Level Security."""
    try:
        payload = decode_token(creds.credentials)
        if payload.get("type") != "access":
            raise _CREDENTIALS_EXC
        user_id = uuid.UUID(payload["sub"])
    except (jwt.PyJWTError, KeyError, ValueError):
        raise _CREDENTIALS_EXC

    user = await db.get(User, user_id)
    if user is None or not user.is_active:
        raise _CREDENTIALS_EXC
    if payload.get("ver", 0) != user.token_version:  # revoked by logout
        raise _CREDENTIALS_EXC

    # Bind tenant for the remainder of this request's transaction (RLS).
    await set_tenant(db, user.tenant_id)
    return user


async def get_current_tenant(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Tenant:
    tenant = await db.get(Tenant, user.tenant_id)
    if tenant is None:
        raise _CREDENTIALS_EXC
    return tenant


def require_owner(user: User = Depends(get_current_user)) -> User:
    from app.models.tenant import UserRole

    if user.role != UserRole.owner:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Owner role required"
        )
    return user


async def get_user_by_email(db: AsyncSession, email: str) -> User | None:
    result = await db.execute(select(User).where(User.email == email.lower()))
    return result.scalar_one_or_none()
