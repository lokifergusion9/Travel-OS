"""Phase 1: itinerary generation, approval, creatives, approval center."""
import json

from tests.conftest import unique_email


def _parse_sse(text: str) -> list[dict]:
    events = []
    for line in text.splitlines():
        if line.startswith("data: "):
            events.append(json.loads(line[len("data: ") :]))
    return events


async def _auth(client) -> dict:
    resp = await client.post(
        "/api/v1/auth/signup",
        json={
            "agency_name": "Trek Co",
            "full_name": "Aadi",
            "email": unique_email(),
            "password": "supersecret123",
        },
    )
    assert resp.status_code == 201, resp.text
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


async def test_itinerary_generate_approve_and_creatives(client):
    headers = await _auth(client)

    # Stream itinerary generation.
    resp = await client.post(
        "/api/v1/trips/generate",
        headers=headers,
        json={"destination": "Spiti Valley", "days": 4, "audience": "college groups",
              "budget_per_person": 12000},
    )
    assert resp.status_code == 200
    events = _parse_sse(resp.text)
    types = [e["type"] for e in events]
    assert "trip_created" in types and "progress" in types and "trip" in types
    trip_id = next(e["trip_id"] for e in events if e["type"] == "trip_created")

    # Trip persisted with days + costing, pending review.
    detail = await client.get(f"/api/v1/trips/{trip_id}", headers=headers)
    body = detail.json()
    assert body["status"] == "pending_review"
    assert len(body["days_plan"]) == 4
    assert body["costing"]["per_person"] == 12000

    # One pending itinerary approval exists.
    appr = await client.get("/api/v1/approvals?status=pending", headers=headers)
    assert any(a["kind"] == "itinerary" for a in appr.json())

    # Approve the itinerary.
    approved = await client.post(f"/api/v1/trips/{trip_id}/approve", headers=headers)
    assert approved.json()["status"] == "approved"

    # Generate creatives (poster + caption + brochure).
    cre = await client.post(
        f"/api/v1/trips/{trip_id}/creatives/generate",
        headers=headers,
        json={"kinds": ["poster", "caption", "brochure"]},
    )
    cre_events = _parse_sse(cre.text)
    kinds = {e["kind"] for e in cre_events if e["type"] == "asset"}
    assert kinds == {"poster", "caption", "brochure"}

    listed = await client.get(f"/api/v1/trips/{trip_id}/creatives", headers=headers)
    assert len(listed.json()) == 3


async def test_creative_approval_decision(client):
    headers = await _auth(client)
    resp = await client.post(
        "/api/v1/trips/generate",
        headers=headers,
        json={"destination": "Goa", "days": 2},
    )
    trip_id = next(
        e["trip_id"] for e in _parse_sse(resp.text) if e["type"] == "trip_created"
    )
    await client.post(
        f"/api/v1/trips/{trip_id}/creatives/generate",
        headers=headers,
        json={"kinds": ["caption"]},
    )
    pending = (await client.get("/api/v1/approvals?status=pending", headers=headers)).json()
    creative_appr = next(a for a in pending if a["kind"] == "creative")
    decided = await client.post(
        f"/api/v1/approvals/{creative_appr['id']}/decide",
        headers=headers,
        json={"decision": "approved"},
    )
    assert decided.json()["status"] == "approved"
