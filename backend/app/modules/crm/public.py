"""Public lead ingestion: Meta Lead Ads webhook + web-form capture (no auth).

Webhook POSTs must carry Meta's ``X-Hub-Signature-256`` (HMAC-SHA256 of the raw
body with META_APP_SECRET) — otherwise anyone who knows a tenant slug could
inject leads. Without a secret configured, unsigned payloads are accepted in
development only; production rejects them.
"""
import hashlib
import hmac
import json

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
from sqlalchemy import select

from app.core.config import settings
from app.core.db import async_session_factory
from app.core.ratelimit import rate_limit
from app.models.tenant import Tenant
from app.modules.crm import service
from app.schemas.crm import CaptureIn

router = APIRouter(prefix="/public", tags=["public"])


async def _tenant_by_slug(slug: str) -> Tenant:
    # tenants is a non-RLS registry table — safe to read without tenant context.
    async with async_session_factory() as s:
        tenant = (await s.execute(select(Tenant).where(Tenant.slug == slug))).scalar_one_or_none()
    if tenant is None:
        raise HTTPException(status_code=404, detail="Unknown agency")
    return tenant


async def _verified_json(request: Request) -> dict:
    """Read the body, enforcing Meta's webhook signature."""
    raw = await request.body()
    secret = settings.meta_app_secret
    if secret:
        expected = "sha256=" + hmac.new(secret.encode(), raw, hashlib.sha256).hexdigest()
        given = request.headers.get("x-hub-signature-256", "")
        if not hmac.compare_digest(expected, given):
            raise HTTPException(status_code=401, detail="Invalid webhook signature")
    elif settings.environment == "production":
        raise HTTPException(status_code=503, detail="Webhook signing secret not configured")
    try:
        body = json.loads(raw or b"{}")
    except ValueError:
        raise HTTPException(status_code=400, detail="Body must be JSON")
    if not isinstance(body, dict):
        raise HTTPException(status_code=400, detail="Body must be a JSON object")
    return body


@router.post(
    "/capture/{slug}",
    status_code=201,
    dependencies=[Depends(rate_limit("capture", 20, 60))],
)
async def capture(slug: str, payload: CaptureIn) -> dict:
    """Embeddable web-form / landing-page lead capture."""
    tenant = await _tenant_by_slug(slug)
    lead_id = await service.ingest_lead(
        tenant.id,
        name=payload.name,
        email=str(payload.email) if payload.email else None,
        phone=payload.phone,
        source="web",
        trip_id=payload.trip_id,
        notes=payload.message,
    )
    return {"ok": True, "lead_id": str(lead_id)}


# --- Meta Lead Ads webhook ---
@router.get("/webhooks/meta")
async def verify_meta_webhook(
    mode: str = Query("", alias="hub.mode"),
    token: str = Query("", alias="hub.verify_token"),
    challenge: str = Query("", alias="hub.challenge"),
) -> Response:
    """Meta verification handshake: echo hub.challenge when the token matches."""
    if mode == "subscribe" and token == settings.meta_webhook_verify_token:
        return Response(content=challenge, media_type="text/plain")
    raise HTTPException(status_code=403, detail="Verification failed")


def _extract_lead_fields(value: dict) -> dict:
    """Pull name/email/phone from Meta lead field_data (or a simple payload)."""
    fields = {"name": value.get("full_name") or value.get("name"),
              "email": value.get("email"), "phone": value.get("phone")}
    for item in value.get("field_data", []) or []:
        key = (item.get("name") or "").lower()
        vals = item.get("values") or []
        val = vals[0] if vals else None
        if key in ("full_name", "name") and val:
            fields["name"] = val
        elif key == "email" and val:
            fields["email"] = val
        elif key in ("phone_number", "phone") and val:
            fields["phone"] = val
    return fields


@router.post("/webhooks/meta")
async def receive_meta_webhook(request: Request, tenant: str = Query("")) -> dict:
    """Receive a leadgen event and create a lead.

    Routing: production maps the Page id (entry[].id) to a connected social
    account (Phase 3). Until then, dev routes via ?tenant=<slug>.
    """
    body = await _verified_json(request)
    if not tenant:
        raise HTTPException(status_code=400, detail="tenant slug required (dev)")
    tenant_obj = await _tenant_by_slug(tenant)

    created = 0
    for entry in body.get("entry", [{"changes": [{"value": body}]}]):
        for change in entry.get("changes", [{"value": body}]):
            value = change.get("value", {})
            fields = _extract_lead_fields(value)
            if not (fields["name"] or fields["email"] or fields["phone"]):
                continue
            await service.ingest_lead(
                tenant_obj.id,
                name=fields["name"] or "Meta lead",
                email=fields["email"],
                phone=fields["phone"],
                source="meta",
                source_meta={k: value.get(k) for k in ("leadgen_id", "form_id", "ad_id") if k in value},
            )
            created += 1
    return {"ok": True, "leads_created": created}


# --- WhatsApp Cloud API webhook (2-way) ---
@router.get("/webhooks/whatsapp")
async def verify_whatsapp_webhook(
    mode: str = Query("", alias="hub.mode"),
    token: str = Query("", alias="hub.verify_token"),
    challenge: str = Query("", alias="hub.challenge"),
) -> Response:
    if mode == "subscribe" and token == settings.whatsapp_verify_token:
        return Response(content=challenge, media_type="text/plain")
    raise HTTPException(status_code=403, detail="Verification failed")


@router.post("/webhooks/whatsapp")
async def receive_whatsapp_webhook(request: Request, tenant: str = Query("")) -> dict:
    """Receive inbound WhatsApp messages and route them to a lead.

    Production maps value.metadata.phone_number_id -> a connected WA account
    (and tenant); dev routes via ?tenant=<slug>.
    """
    body = await _verified_json(request)
    if not tenant:
        raise HTTPException(status_code=400, detail="tenant slug required (dev)")
    tenant_obj = await _tenant_by_slug(tenant)

    received = 0
    for entry in body.get("entry", []):
        for change in entry.get("changes", []):
            value = change.get("value", {})
            contacts = {c.get("wa_id"): (c.get("profile") or {}).get("name")
                        for c in value.get("contacts", [])}
            for msg in value.get("messages", []):
                if msg.get("type") != "text":
                    continue
                frm = msg.get("from", "")
                text = (msg.get("text") or {}).get("body", "")
                if not (frm and text):
                    continue
                await service.ingest_whatsapp_inbound(
                    tenant_obj.id, frm, contacts.get(frm), text
                )
                received += 1
    return {"ok": True, "messages_received": received}
