"""Password hashing (bcrypt), JWT tokens, and credential encryption."""
from datetime import datetime, timedelta, timezone
from typing import Any, Literal

import bcrypt
import jwt
from cryptography.fernet import Fernet

from app.core.config import settings

TokenType = Literal["access", "refresh"]


# --- Passwords ---
def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(password: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode(), hashed.encode())
    except ValueError:
        return False


# --- JWT ---
def _create_token(
    subject: str, tenant_id: str, ttl: timedelta, kind: TokenType, version: int
) -> str:
    now = datetime.now(timezone.utc)
    payload: dict[str, Any] = {
        "sub": subject,
        "tid": tenant_id,
        "type": kind,
        "ver": version,
        "iat": now,
        "exp": now + ttl,
    }
    return jwt.encode(payload, settings.secret_key, algorithm=settings.jwt_algorithm)


def create_access_token(user_id: str, tenant_id: str, version: int = 0) -> str:
    return _create_token(
        user_id,
        tenant_id,
        timedelta(minutes=settings.access_token_expire_minutes),
        "access",
        version,
    )


def create_refresh_token(user_id: str, tenant_id: str, version: int = 0) -> str:
    return _create_token(
        user_id,
        tenant_id,
        timedelta(days=settings.refresh_token_expire_days),
        "refresh",
        version,
    )


def decode_token(token: str) -> dict[str, Any]:
    return jwt.decode(
        token, settings.secret_key, algorithms=[settings.jwt_algorithm]
    )


# --- Per-tenant credential encryption (Meta tokens, email/SMS keys) ---
def _fernet() -> Fernet:
    key = settings.credentials_encryption_key
    if not key:
        # Dev fallback: derive a stable key from secret_key. Set a real
        # CREDENTIALS_ENCRYPTION_KEY in production.
        import base64
        import hashlib

        key = base64.urlsafe_b64encode(
            hashlib.sha256(settings.secret_key.encode()).digest()
        ).decode()
    return Fernet(key.encode() if isinstance(key, str) else key)


def encrypt_secret(plaintext: str) -> str:
    return _fernet().encrypt(plaintext.encode()).decode()


def decrypt_secret(token: str) -> str:
    return _fernet().decrypt(token.encode()).decode()
