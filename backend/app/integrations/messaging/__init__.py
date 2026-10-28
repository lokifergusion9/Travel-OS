"""Outbound messaging (Email/SMS), pluggable and free-first.

Phase 2 ships the console sender (logs to stdout) as the default so the CRM
works with zero credentials. Resend/Brevo (email) and MSG91/Fast2SMS (SMS) are
wired the same way later. WhatsApp Cloud API arrives in a later phase.
"""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass

import httpx

from app.core.config import settings

logger = logging.getLogger("travelos.messaging")

_PLACEHOLDER = re.compile(r"\{\{\s*(\w+)\s*\}\}")


def render(template: str, context: dict[str, str]) -> str:
    """Replace {{name}} placeholders; unknown ones become empty strings."""
    return _PLACEHOLDER.sub(lambda m: str(context.get(m.group(1), "")), template)


@dataclass
class SendResult:
    ok: bool
    provider: str
    detail: str = ""


# --- Email ---
async def send_email(to: str, subject: str, body: str) -> SendResult:
    provider = settings.email_provider
    if provider == "resend" and settings.resend_api_key:
        return await _resend(to, subject, body)
    if provider == "brevo" and settings.brevo_api_key:
        return await _brevo(to, subject, body)
    logger.info("[EMAIL→%s] %s\n%s", to, subject, body)
    return SendResult(True, "console")


async def _resend(to: str, subject: str, body: str) -> SendResult:
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(
            "https://api.resend.com/emails",
            headers={"Authorization": f"Bearer {settings.resend_api_key}"},
            json={"from": settings.email_from, "to": [to], "subject": subject, "html": body},
        )
    return SendResult(resp.is_success, "resend", resp.text[:200])


async def _brevo(to: str, subject: str, body: str) -> SendResult:
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(
            "https://api.brevo.com/v3/smtp/email",
            headers={"api-key": settings.brevo_api_key},
            json={
                "sender": {"email": settings.email_from},
                "to": [{"email": to}],
                "subject": subject,
                "htmlContent": body,
            },
        )
    return SendResult(resp.is_success, "brevo", resp.text[:200])


# --- SMS ---
async def send_sms(to: str, body: str) -> SendResult:
    provider = settings.sms_provider
    if provider == "fast2sms" and settings.fast2sms_api_key:
        return await _fast2sms(to, body)
    # MSG91 and others follow the same pattern; default to console.
    logger.info("[SMS→%s] %s", to, body)
    return SendResult(True, "console")


async def _fast2sms(to: str, body: str) -> SendResult:
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.get(
            "https://www.fast2sms.com/dev/bulkV2",
            params={"authorization": settings.fast2sms_api_key, "route": "q",
                    "message": body, "numbers": to},
        )
    return SendResult(resp.is_success, "fast2sms", resp.text[:200])


# --- WhatsApp (Cloud API) ---
async def send_whatsapp(to: str, body: str) -> SendResult:
    if settings.whatsapp_provider == "cloud" and settings.whatsapp_token:
        return await _whatsapp_cloud(to, body)
    logger.info("[WHATSAPP→%s] %s", to, body)
    return SendResult(True, "console")


async def _whatsapp_cloud(to: str, body: str) -> SendResult:
    """Send a free-form text via the WhatsApp Cloud API (only valid inside the
    24h customer-service window; outside it a pre-approved template is required)."""
    url = f"https://graph.facebook.com/v21.0/{settings.whatsapp_phone_number_id}/messages"
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(
            url,
            headers={"Authorization": f"Bearer {settings.whatsapp_token}"},
            json={"messaging_product": "whatsapp", "to": to, "type": "text",
                  "text": {"body": body}},
        )
    return SendResult(resp.is_success, "whatsapp", resp.text[:200])


async def send(channel: str, *, to: str, subject: str, body: str) -> SendResult:
    if channel == "sms":
        return await send_sms(to, body)
    if channel == "whatsapp":
        return await send_whatsapp(to, body)
    return await send_email(to, subject or "A message from your travel agency", body)
