"""Server-Sent Events helpers."""
import json
from typing import Any


def sse(data: dict[str, Any]) -> str:
    """Format a dict as one SSE message."""
    return f"data: {json.dumps(data, ensure_ascii=False)}\n\n"
