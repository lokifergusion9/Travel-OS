"""Phase 2: leads, first-touch (HITL), inbound classification, ingestion, scheduler."""
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import select

from app.core.db import async_session_factory
from app.models.lead import ScheduledFollowup
from tests.conftest import unique_email


async def _signup(client) -> tuple[dict, dict]:
    resp = await client.post(
        "/api/v1/auth/signup",
        json={"agency_name": "Trek Co", "full_name": "Aadi",
              "email": unique_email(), "password": "supersecret123"},
    )
    assert resp.status_code == 201
    headers = {"Authorization": f"Bearer {resp.json()['access_token']}"}
    me = (await client.get("/api/v1/auth/me", headers=headers)).json()
    return headers, me


async def test_lead_first_touch_is_hitl_then_approved(client):
    headers, me = await _signup(client)
    lead = (await client.post("/api/v1/leads", headers=headers,
                              json={"name": "Rahul", "email": "rahul@example.com"})).json()
    assert lead["stage"] == "new"

    detail = (await client.get(f"/api/v1/leads/{lead['id']}", headers=headers)).json()
    drafts = [m for m in detail["messages"] if m["direction"] == "outbound"]
    assert len(drafts) == 1 and drafts[0]["status"] == "draft"
    assert any(a["type"] == "created" for a in detail["activities"])

    # First-touch waits in the Approval Center (HITL, auto_followup off by default).
    pending = (await client.get("/api/v1/approvals?status=pending", headers=headers)).json()
    msg_appr = next(a for a in pending if a["kind"] == "message")
    decided = await client.post(f"/api/v1/approvals/{msg_appr['id']}/decide",
                                headers=headers, json={"decision": "approved"})
    assert decided.status_code == 200

    after = (await client.get(f"/api/v1/leads/{lead['id']}", headers=headers)).json()
    assert after["stage"] == "contacted"
    assert any(m["status"] == "sent" for m in after["messages"])


async def test_inbound_is_classified(client):
    headers, _ = await _signup(client)
    lead = (await client.post("/api/v1/leads", headers=headers,
                              json={"name": "Priya", "email": "priya@example.com"})).json()
    resp = await client.post(f"/api/v1/leads/{lead['id']}/inbound", headers=headers,
                             json={"body": "How much does it cost?"})
    assert resp.json()["stage"] == "interested"
    detail = (await client.get(f"/api/v1/leads/{lead['id']}", headers=headers)).json()
    inbound = next(a for a in detail["activities"] if a["type"] == "message_received")
    assert inbound["meta"]["intent"] == "price"


async def test_meta_webhook_and_web_capture(client):
    headers, me = await _signup(client)
    slug = me["tenant"]["slug"]

    meta_payload = {
        "entry": [{"changes": [{"value": {
            "leadgen_id": "lg1", "form_id": "f1", "ad_id": "a1",
            "field_data": [
                {"name": "full_name", "values": ["Meta Lead"]},
                {"name": "email", "values": ["meta@example.com"]},
            ],
        }}]}]
    }
    wh = await client.post(f"/api/v1/public/webhooks/meta?tenant={slug}", json=meta_payload)
    assert wh.json()["leads_created"] == 1

    cap = await client.post(f"/api/v1/public/capture/{slug}",
                            json={"name": "Web Lead", "email": "web@example.com"})
    assert cap.status_code == 201

    leads = (await client.get("/api/v1/leads", headers=headers)).json()
    sources = {l["source"] for l in leads}
    assert {"meta", "web"} <= sources


async def test_webhook_verification(client):
    ok = await client.get(
        "/api/v1/public/webhooks/meta",
        params={"hub.mode": "subscribe", "hub.verify_token": "travelos-verify",
                "hub.challenge": "12345"},
    )
    assert ok.status_code == 200 and ok.text == "12345"
    bad = await client.get(
        "/api/v1/public/webhooks/meta",
        params={"hub.mode": "subscribe", "hub.verify_token": "wrong", "hub.challenge": "x"},
    )
    assert bad.status_code == 403


async def test_scheduler_processes_due_followup(client):
    from app.workers.scheduler import process_due_followups

    headers, me = await _signup(client)
    tenant_id = uuid.UUID(me["tenant"]["id"])
    # Auto mode so the reminder actually sends (not queued for approval).
    await client.post("/api/v1/settings/auto-followup?enabled=true", headers=headers)
    lead = (await client.post("/api/v1/leads", headers=headers,
                              json={"name": "Sam", "email": "sam@example.com"})).json()

    # Force a due reminder (non-RLS internal table; insert directly).
    async with async_session_factory() as s:
        async with s.begin():
            s.add(ScheduledFollowup(
                tenant_id=tenant_id, lead_id=uuid.UUID(lead["id"]),
                run_at=datetime.now(timezone.utc) - timedelta(minutes=1),
                channel="email", step=1, status="scheduled",
            ))

    processed = await process_due_followups()
    assert processed >= 1

    detail = (await client.get(f"/api/v1/leads/{lead['id']}", headers=headers)).json()
    sent = [m for m in detail["messages"] if m["direction"] == "outbound" and m["status"] == "sent"]
    assert len(sent) >= 2  # first touch (auto) + the reminder

    async with async_session_factory() as s:
        rows = (await s.execute(
            select(ScheduledFollowup).where(ScheduledFollowup.lead_id == uuid.UUID(lead["id"]))
        )).scalars().all()
    assert any(r.status == "sent" for r in rows)
