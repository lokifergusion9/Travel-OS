"""Security hardening: webhook signatures, token revocation, refresh cookie,
rate limiting."""
import hashlib
import hmac
import json
import uuid

import pytest
from fastapi import HTTPException
from starlette.requests import Request

from app.core.config import settings
from app.core.ratelimit import rate_limit
from app.core.security import create_access_token
from tests.conftest import unique_email


async def _signup(client):
    resp = await client.post("/api/v1/auth/signup", json={
        "agency_name": "Hardening Co", "full_name": "Sec Tester",
        "email": unique_email(), "password": "supersecret1",
    })
    assert resp.status_code == 201
    tokens = resp.json()
    me = (await client.get("/api/v1/auth/me",
                           headers={"Authorization": f"Bearer {tokens['access_token']}"})).json()
    return tokens, me


def _sign(secret: str, raw: bytes) -> str:
    return "sha256=" + hmac.new(secret.encode(), raw, hashlib.sha256).hexdigest()


async def test_webhook_rejects_bad_signature_and_accepts_good(client, monkeypatch):
    monkeypatch.setattr(settings, "meta_app_secret", "test-app-secret")
    _, me = await _signup(client)
    url = f"/api/v1/public/webhooks/meta?tenant={me['tenant']['slug']}"
    raw = json.dumps({"full_name": "Signed Lead", "email": "signed@example.com"}).encode()
    headers = {"content-type": "application/json"}

    unsigned = await client.post(url, content=raw, headers=headers)
    assert unsigned.status_code == 401

    forged = await client.post(url, content=raw,
                               headers={**headers, "X-Hub-Signature-256": _sign("wrong", raw)})
    assert forged.status_code == 401

    good = await client.post(url, content=raw, headers={
        **headers, "X-Hub-Signature-256": _sign("test-app-secret", raw)})
    assert good.status_code == 200 and good.json()["leads_created"] == 1


async def test_production_rejects_webhooks_without_secret(client, monkeypatch):
    _, me = await _signup(client)
    monkeypatch.setattr(settings, "meta_app_secret", "")
    monkeypatch.setattr(settings, "environment", "production")
    resp = await client.post(
        f"/api/v1/public/webhooks/whatsapp?tenant={me['tenant']['slug']}", json={"entry": []})
    assert resp.status_code == 503


async def test_logout_revokes_access_and_refresh(client):
    tokens, _ = await _signup(client)
    auth = {"Authorization": f"Bearer {tokens['access_token']}"}
    assert (await client.post("/api/v1/auth/logout", headers=auth)).status_code == 204

    assert (await client.get("/api/v1/auth/me", headers=auth)).status_code == 401
    again = await client.post("/api/v1/auth/refresh",
                              json={"refresh_token": tokens["refresh_token"]})
    assert again.status_code == 401


async def test_refresh_via_httponly_cookie(client):
    resp = await client.post("/api/v1/auth/signup", json={
        "agency_name": "Cookie Co", "full_name": "C", "email": unique_email(),
        "password": "supersecret1",
    })
    set_cookie = resp.headers["set-cookie"].lower()
    assert settings.refresh_cookie_name in set_cookie and "httponly" in set_cookie

    # httpx keeps the cookie jar; no body needed.
    refreshed = await client.post("/api/v1/auth/refresh")
    assert refreshed.status_code == 200 and refreshed.json()["access_token"]


async def test_refresh_with_malformed_subject_is_401(client):
    from app.core.security import _create_token
    from datetime import timedelta

    bad = _create_token("not-a-uuid", str(uuid.uuid4()), timedelta(minutes=5), "refresh", 0)
    resp = await client.post("/api/v1/auth/refresh", json={"refresh_token": bad})
    assert resp.status_code == 401


async def test_stale_token_version_is_rejected(client):
    tokens, me = await _signup(client)
    stale = create_access_token(me["user"]["id"], me["tenant"]["id"], version=99)
    resp = await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {stale}"})
    assert resp.status_code == 401


async def test_rate_limit_blocks_after_limit(monkeypatch):
    monkeypatch.setattr(settings, "rate_limit_enabled", True)
    dep = rate_limit(f"test-{uuid.uuid4().hex}", 3, 60)
    request = Request({"type": "http", "headers": [], "client": ("10.0.0.9", 1234)})
    for _ in range(3):
        await dep(request)
    with pytest.raises(HTTPException) as exc:
        await dep(request)
    assert exc.value.status_code == 429
