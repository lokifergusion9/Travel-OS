"""Small shared utilities."""
import re
import secrets

_slug_re = re.compile(r"[^a-z0-9]+")


def slugify(value: str) -> str:
    slug = _slug_re.sub("-", value.lower()).strip("-")
    return slug or "agency"


def random_suffix(n: int = 4) -> str:
    return secrets.token_hex(n // 2 + 1)[:n]
