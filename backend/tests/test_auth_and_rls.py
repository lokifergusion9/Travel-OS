"""End-to-end auth flow + tenant Row-Level Security isolation."""
import uuid

from sqlalchemy import text

from app.core.db import async_session_factory, set_tenant
from tests.conftest import unique_email


async def _signup(client, agency: str):
    email = unique_email()
    resp = await client.post(
        "/api/v1/auth/signup",
        json={
            "agency_name": agency,
            "full_name": "Owner",
            "email": email,
            "password": "supersecret123",
        },
    )
    assert resp.status_code == 201, resp.text
    return email, resp.json()


async def test_signup_login_me(client):
    email, tokens = await _signup(client, "Himalaya Treks")
    assert tokens["access_token"]

    login = await client.post(
        "/api/v1/auth/login", json={"email": email, "password": "supersecret123"}
    )
    assert login.status_code == 200

    me = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {tokens['access_token']}"},
    )
    assert me.status_code == 200
    body = me.json()
    assert body["user"]["email"] == email
    assert body["tenant"]["name"] == "Himalaya Treks"
    assert body["user"]["role"] == "owner"


async def test_duplicate_email_rejected(client):
    email, _ = await _signup(client, "Coastal Tours")
    dup = await client.post(
        "/api/v1/auth/signup",
        json={
            "agency_name": "Other",
            "full_name": "X",
            "email": email,
            "password": "supersecret123",
        },
    )
    assert dup.status_code == 409


async def test_rls_blocks_cross_tenant_reads(client):
    """audit_log rows of tenant A must be invisible when bound to tenant B."""
    _, a = await _signup(client, "Agency A")
    _, b = await _signup(client, "Agency B")

    # Resolve tenant ids from /me.
    async def tenant_id(tokens) -> uuid.UUID:
        me = await client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {tokens['access_token']}"},
        )
        return uuid.UUID(me.json()["tenant"]["id"])

    tid_a = await tenant_id(a)
    tid_b = await tenant_id(b)
    marker = uuid.uuid4().hex

    # Insert an audit row for tenant A (RLS WITH CHECK enforces the binding).
    async with async_session_factory() as s:
        async with s.begin():
            await set_tenant(s, tid_a)
            await s.execute(
                text(
                    "INSERT INTO audit_log (id, tenant_id, action, meta) "
                    "VALUES (:id, :tid, :action, '{}'::jsonb)"
                ),
                {"id": uuid.uuid4(), "tid": tid_a, "action": marker},
            )

    # Bound to A: row is visible.
    async with async_session_factory() as s:
        async with s.begin():
            await set_tenant(s, tid_a)
            seen_a = (
                await s.execute(
                    text("SELECT count(*) FROM audit_log WHERE action = :m"),
                    {"m": marker},
                )
            ).scalar()
    assert seen_a == 1

    # Bound to B: RLS hides A's row.
    async with async_session_factory() as s:
        async with s.begin():
            await set_tenant(s, tid_b)
            seen_b = (
                await s.execute(
                    text("SELECT count(*) FROM audit_log WHERE action = :m"),
                    {"m": marker},
                )
            ).scalar()
    assert seen_b == 0
