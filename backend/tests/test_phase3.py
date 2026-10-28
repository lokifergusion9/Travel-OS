"""Phase 3: sourcing (vendors -> outreach -> deals) and publishing (IG dev)."""
import json
import uuid
from datetime import datetime, timedelta, timezone

from tests.conftest import unique_email


async def _signup(client) -> dict:
    resp = await client.post(
        "/api/v1/auth/signup",
        json={"agency_name": "Trek Co", "full_name": "Aadi",
              "email": unique_email(), "password": "supersecret123"},
    )
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


async def _make_trip(client, headers) -> str:
    resp = await client.post("/api/v1/trips/generate", headers=headers,
                             json={"destination": "Manali", "days": 3})
    for line in resp.text.splitlines():
        if line.startswith("data: "):
            ev = json.loads(line[6:])
            if ev["type"] == "trip_created":
                return ev["trip_id"]
    raise AssertionError("no trip_created event")


async def test_sourcing_outreach_and_deal_flow(client):
    headers = await _signup(client)
    trip_id = await _make_trip(client, headers)

    # Add a hotel + a transport vendor.
    for v in [
        {"name": "Snow Peak Resort", "type": "hotel", "contact_email": "hotel@x.com"},
        {"name": "Hill Cabs", "type": "transport", "contact_email": "cabs@x.com"},
    ]:
        assert (await client.post("/api/v1/vendors", headers=headers, json=v)).status_code == 201

    # Generate outreach -> one deal per vendor, each queued for approval (HITL).
    gen = await client.post(f"/api/v1/trips/{trip_id}/sourcing/generate", headers=headers)
    assert gen.json()["deals_created"] == 2

    deals = (await client.get(f"/api/v1/deals?trip_id={trip_id}", headers=headers)).json()
    assert len(deals) == 2 and all(d["sent"] is False for d in deals)

    pending = (await client.get("/api/v1/approvals?status=pending", headers=headers)).json()
    sourcing_apprs = [a for a in pending if a["kind"] == "sourcing"]
    assert len(sourcing_apprs) == 2

    # Approve one outreach -> deal marked sent.
    await client.post(f"/api/v1/approvals/{sourcing_apprs[0]['id']}/decide",
                      headers=headers, json={"decision": "approved"})
    deal_id = sourcing_apprs[0]["entity_id"]
    after = (await client.get(f"/api/v1/deals?trip_id={trip_id}", headers=headers)).json()
    assert any(d["id"] == deal_id and d["sent"] for d in after)

    # Negotiate -> confirm with terms.
    upd = await client.patch(f"/api/v1/deals/{deal_id}", headers=headers,
                             json={"status": "confirmed", "amount": 2500, "terms": "20% group discount"})
    assert upd.json()["status"] == "confirmed" and upd.json()["amount"] == 2500


async def test_publishing_dev_connect_and_publish(client):
    headers = await _signup(client)

    acct = await client.post("/api/v1/publishing/connect/dev", headers=headers,
                             json={"account_name": "@trekco"})
    assert acct.status_code == 201 and acct.json()["is_dev"] is True

    post = await client.post("/api/v1/publishing/posts", headers=headers,
                             json={"caption": "Manali calling!", "image_url": "/storage/x/p.svg"})
    post_id = post.json()["id"]
    assert post.json()["status"] == "scheduled"

    published = await client.post(f"/api/v1/publishing/posts/{post_id}/publish", headers=headers)
    body = published.json()
    assert body["status"] == "published"
    assert body["result"]["mock"] is True and body["result"]["permalink"]


async def test_post_scheduler_publishes_due(client):
    from app.core.db import async_session_factory
    from app.models.publishing import ScheduledPost
    from app.workers.scheduler import process_due_posts

    headers = await _signup(client)
    me = (await client.get("/api/v1/auth/me", headers=headers)).json()
    tenant_id = uuid.UUID(me["tenant"]["id"])
    await client.post("/api/v1/publishing/connect/dev", headers=headers, json={"account_name": "@a"})

    post = await client.post("/api/v1/publishing/posts", headers=headers,
                             json={"caption": "due post", "image_url": "/storage/x/p.svg",
                                   "scheduled_at": (datetime.now(timezone.utc) - timedelta(minutes=1)).isoformat()})
    post_id = uuid.UUID(post.json()["id"])

    assert await process_due_posts() >= 1
    async with async_session_factory() as s:
        from app.core.db import set_tenant
        async with s.begin():
            await set_tenant(s, tenant_id)
            refreshed = await s.get(ScheduledPost, post_id)
            assert refreshed.status == "published"
