"""Object storage abstraction. Local filesystem in dev, S3 in prod (Phase 5).

Files are namespaced per tenant and served (local) under ``/storage``.
"""
from __future__ import annotations

import abc
import uuid
from pathlib import Path

from app.core.config import settings

STORAGE_DIR = Path(settings.storage_dir)
STORAGE_URL_PREFIX = "/storage"


class StorageBackend(abc.ABC):
    @abc.abstractmethod
    def save(self, tenant_id: str, data: bytes, ext: str) -> str:
        """Persist bytes and return a servable URL path."""


class LocalStorage(StorageBackend):
    def save(self, tenant_id: str, data: bytes, ext: str) -> str:
        name = f"{uuid.uuid4().hex}.{ext}"
        folder = STORAGE_DIR / tenant_id
        folder.mkdir(parents=True, exist_ok=True)
        (folder / name).write_bytes(data)
        return f"{STORAGE_URL_PREFIX}/{tenant_id}/{name}"


_CONTENT_TYPES = {
    "svg": "image/svg+xml",
    "png": "image/png",
    "jpg": "image/jpeg",
    "jpeg": "image/jpeg",
    "pdf": "application/pdf",
    "mp4": "video/mp4",
}


class S3Storage(StorageBackend):
    """Uploads to S3 and returns a public URL (CloudFront domain if configured).

    A public URL is required for real Instagram publishing — the Graph API
    fetches the image by URL.
    """

    def __init__(self) -> None:
        import boto3  # imported lazily so dev doesn't need boto3

        self._client = boto3.client("s3", region_name=settings.aws_region)
        self._bucket = settings.s3_bucket

    def save(self, tenant_id: str, data: bytes, ext: str) -> str:
        key = f"{tenant_id}/{uuid.uuid4().hex}.{ext}"
        self._client.put_object(
            Bucket=self._bucket,
            Key=key,
            Body=data,
            ContentType=_CONTENT_TYPES.get(ext, "application/octet-stream"),
            CacheControl="public, max-age=31536000",
        )
        base = settings.asset_public_base_url.rstrip("/")
        if base:
            return f"{base}/{key}"
        return f"https://{self._bucket}.s3.{settings.aws_region}.amazonaws.com/{key}"


def get_storage() -> StorageBackend:
    if settings.storage_backend == "s3":
        return S3Storage()
    return LocalStorage()
