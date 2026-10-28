"""Image generation providers (posters / creatives), free-tier first.

- MockImageProvider: keyless, networkless SVG poster. Used in tests / when offline.
- PollinationsProvider: free, keyless (Flux). Default for dev.
- GeminiImageProvider: Gemini 2.5 Flash Image ("Nano Banana"), ~500 free/day,
  via REST so we don't pull in an extra SDK.

All return a GeneratedImage (bytes + content type + extension); storage persists it.
"""
from __future__ import annotations

import abc
import base64
import html
from dataclasses import dataclass
from urllib.parse import quote

import httpx

from app.core.config import settings


@dataclass
class GeneratedImage:
    data: bytes
    content_type: str
    ext: str


class ImageProvider(abc.ABC):
    @abc.abstractmethod
    async def generate(
        self, prompt: str, *, width: int = 1024, height: int = 1024
    ) -> GeneratedImage:
        """Generate a single image."""


class MockImageProvider(ImageProvider):
    """Renders the prompt onto a gradient SVG — deterministic, no network."""

    async def generate(
        self, prompt: str, *, width: int = 1024, height: int = 1024
    ) -> GeneratedImage:
        safe = html.escape(prompt[:120])
        svg = f"""<svg xmlns='http://www.w3.org/2000/svg' width='{width}' height='{height}'>
  <defs>
    <linearGradient id='g' x1='0' y1='0' x2='1' y2='1'>
      <stop offset='0%' stop-color='#2dd4bf'/>
      <stop offset='50%' stop-color='#1f7aed'/>
      <stop offset='100%' stop-color='#ff6b35'/>
    </linearGradient>
  </defs>
  <rect width='100%' height='100%' fill='url(#g)'/>
  <text x='50%' y='46%' fill='white' font-family='sans-serif' font-size='42'
        font-weight='bold' text-anchor='middle'>TravelOS</text>
  <foreignObject x='8%' y='52%' width='84%' height='40%'>
    <div xmlns='http://www.w3.org/1999/xhtml'
         style='color:white;font-family:sans-serif;font-size:24px;text-align:center'>
      {safe}
    </div>
  </foreignObject>
</svg>"""
        return GeneratedImage(svg.encode(), "image/svg+xml", "svg")


class PollinationsProvider(ImageProvider):
    """Free, keyless image generation (Flux). https://pollinations.ai"""

    BASE = "https://image.pollinations.ai/prompt"

    async def generate(
        self, prompt: str, *, width: int = 1024, height: int = 1024
    ) -> GeneratedImage:
        url = f"{self.BASE}/{quote(prompt)}"
        params = {"width": width, "height": height, "nologo": "true", "model": "flux"}
        async with httpx.AsyncClient(timeout=120) as client:
            resp = await client.get(url, params=params)
            resp.raise_for_status()
            ct = resp.headers.get("content-type", "image/jpeg")
            ext = "png" if "png" in ct else "jpg"
            return GeneratedImage(resp.content, ct, ext)


class GeminiImageProvider(ImageProvider):
    """Gemini Flash Image via the Generative Language REST API."""

    def __init__(self) -> None:
        if not settings.gemini_api_key:
            raise RuntimeError("GEMINI_API_KEY is required for the gemini image provider")
        self.model = settings.gemini_image_model
        self.api_key = settings.gemini_api_key

    async def generate(
        self, prompt: str, *, width: int = 1024, height: int = 1024
    ) -> GeneratedImage:
        url = (
            f"https://generativelanguage.googleapis.com/v1beta/models/"
            f"{self.model}:generateContent"
        )
        body = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"responseModalities": ["IMAGE"]},
        }
        async with httpx.AsyncClient(timeout=120) as client:
            resp = await client.post(url, params={"key": self.api_key}, json=body)
            resp.raise_for_status()
            data = resp.json()
        for part in data["candidates"][0]["content"]["parts"]:
            inline = part.get("inlineData") or part.get("inline_data")
            if inline:
                ct = inline.get("mimeType", "image/png")
                ext = "png" if "png" in ct else "jpg"
                return GeneratedImage(base64.b64decode(inline["data"]), ct, ext)
        raise RuntimeError("Gemini returned no image data")


def build_image_provider(name: str | None = None) -> ImageProvider:
    name = name or settings.llm_image_provider
    if name == "mock":
        return MockImageProvider()
    if name == "gemini":
        return GeminiImageProvider()
    if name == "pollinations":
        return PollinationsProvider()
    raise ValueError(f"Unknown image provider: {name}")
