"""Phase 4: WhatsApp 2-way, reel generation, analytics."""
import json

from tests.conftest import unique_email


async def _signup(client):
    resp = await client.post(
        "/api/v1/auth/signup",
        json={"agency_name": "Trek Co", "full_name": "Aadi",
              "email": unique_email(), "password": "supersecret123"},
    )
    headers = {"Authorization": f"Bearer {resp.json()['access_token']}"}
    me = (await client.get("/api/v1/auth/me", headers=headers)).json()
    return headers, me


def _parse_sse(text: str):
    return [json.loads(l[6:]) for l in text.splitlines() if l.startswith("data: ")]


async def _make_trip(client, headers) -> str:
    resp = await client.post("/api/v1/trips/generate", headers=headers,
                             json={"destination": "Goa", "days": 3})
    return next(e["trip_id"] for e in _parse_sse(resp.text) if e["type"] == "trip_created")


async def test_whatsapp_inbound_creates_and_classifies_lead(client):
    headers, me = await _signup(client)
    slug = me["tenant"]["slug"]
    payload = {"entry": [{"changes": [{"value": {
        "metadata": {"phone_number_id": "123"},
        "contacts": [{"wa_id": "919812345678", "profile": {"name": "Ravi"}}],
        "messages": [{"from": "919812345678", "type": "text",
                      "text": {"body": "how much for goa?"}, "id": "m1"}],
    }}]}]}
    wh = await client.post(f"/api/v1/public/webhooks/whatsapp?tenant={slug}", json=payload)
    assert wh.json()["messages_received"] == 1

    leads = (await client.get("/api/v1/leads", headers=headers)).json()
    wa = next(l for l in leads if l["source"] == "whatsapp")
    assert wa["phone"] == "919812345678" and wa["stage"] == "interested"

    detail = (await client.get(f"/api/v1/leads/{wa['id']}", headers=headers)).json()
    received = next(a for a in detail["activities"] if a["type"] == "message_received")
    assert received["meta"]["intent"] == "price"


async def test_whatsapp_verification(client):
    ok = await client.get("/api/v1/public/webhooks/whatsapp",
                          params={"hub.mode": "subscribe",
                                  "hub.verify_token": "travelos-wa-verify",
                                  "hub.challenge": "99"})
    assert ok.status_code == 200 and ok.text == "99"


async def test_reel_generation(client):
    headers, _ = await _signup(client)
    trip_id = await _make_trip(client, headers)
    resp = await client.post(f"/api/v1/trips/{trip_id}/creatives/generate", headers=headers,
                             json={"kinds": ["reel"]})
    kinds = {e["kind"] for e in _parse_sse(resp.text) if e["type"] == "asset"}
    assert "reel" in kinds

    creatives = (await client.get(f"/api/v1/trips/{trip_id}/creatives", headers=headers)).json()
    reel = next(c for c in creatives if c["kind"] == "reel")
    assert reel["url"] and reel["meta"].get("scenes")
    assert len(reel["meta"]["scenes"]) >= 3


async def test_analytics_overview(client):
    headers, _ = await _signup(client)
    # Two leads; move one to won.
    l1 = (await client.post("/api/v1/leads", headers=headers,
                            json={"name": "A", "email": "a@x.com"})).json()
    await client.post("/api/v1/leads", headers=headers, json={"name": "B", "email": "b@x.com"})
    await client.patch(f"/api/v1/leads/{l1['id']}/stage", headers=headers, json={"stage": "won"})

    data = (await client.get("/api/v1/analytics/overview", headers=headers)).json()
    assert data["kpis"]["leads_total"] == 2
    assert data["kpis"]["leads_won"] == 1
    assert data["kpis"]["conversion_rate"] == 50.0
    won_row = next(f for f in data["funnel"] if f["stage"] == "won")
    assert won_row["count"] == 1
    assert sum(s["count"] for s in data["by_source"]) == 2
