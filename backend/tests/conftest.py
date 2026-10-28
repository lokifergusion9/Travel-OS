"""Pytest fixtures. Requires the Postgres from docker-compose to be running and
migrated (``alembic upgrade head``). Run from backend/: ``pytest``."""
import os
import uuid

# Many tests sign up from the same client IP; limits get their own test.
os.environ.setdefault("RATE_LIMIT_ENABLED", "false")

import httpx
import pytest
from asgi_lifespan import LifespanManager

from app.core.db import async_session_factory, set_tenant
from app.main import app


@pytest.fixture
async def client():
    async with LifespanManager(app):
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
            yield c


@pytest.fixture
async def db():
    async with async_session_factory() as session:
        async with session.begin():
            yield session


def unique_email() -> str:
    return f"user-{uuid.uuid4().hex[:8]}@example.com"


__all__ = ["client", "db", "set_tenant", "unique_email"]
