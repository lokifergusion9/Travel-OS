"""Async database engine, session, and tenant Row-Level Security helpers.

Multi-tenancy is enforced at two layers:
  1. Application: every tenant-scoped query carries ``tenant_id``.
  2. Database: Postgres RLS policies filter rows by the ``app.current_tenant``
     GUC, set per request. The app connects as a NON-superuser role
     (``travelos_app``) so RLS is actually enforced (superusers bypass it).

Routes must NOT call ``session.commit()`` themselves — ``get_db`` wraps each
request in a single transaction and commits on success / rolls back on error.
This also makes ``SET LOCAL`` of the tenant GUC scoped to the request.
"""
import os
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool

from app.core.config import settings

# Under pytest each test gets a fresh event loop; a pooled asyncpg connection
# would then be closed on a dead loop. NullPool opens/closes per checkout to
# avoid that. Production keeps normal pooling.
_engine_kwargs: dict = {"echo": settings.sql_echo}
if os.getenv("PYTEST_VERSION") is not None:
    _engine_kwargs["poolclass"] = NullPool
else:
    _engine_kwargs["pool_pre_ping"] = True

engine = create_async_engine(settings.database_url, **_engine_kwargs)

async_session_factory = async_sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False, autoflush=False
)


async def set_tenant(
    session: AsyncSession, tenant_id: UUID | str, *, local: bool = True
) -> None:
    """Bind the session to a tenant for RLS.

    local=True (default) scopes the GUC to the current transaction — right for a
    one-transaction request. local=False sets it at connection level so it
    survives the multiple await points of a streaming response; callers using
    that must reset it (see ``tenant_session``).
    """
    await session.execute(
        text("SELECT set_config('app.current_tenant', :tid, :local)"),
        {"tid": str(tenant_id), "local": local},
    )


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency: one transaction per request."""
    async with async_session_factory() as session:
        async with session.begin():
            yield session


@asynccontextmanager
async def tenant_session(tenant_id: UUID | str) -> AsyncGenerator[AsyncSession, None]:
    """A fresh tenant-bound session+transaction.

    Used by streaming (SSE) endpoints: their response body runs after the
    request's own transaction has closed, so writes need their own transaction
    with the RLS tenant GUC set here.
    """
    async with async_session_factory() as session:
        async with session.begin():
            await set_tenant(session, tenant_id)
            yield session
