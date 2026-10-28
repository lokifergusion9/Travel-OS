"""Factory for chat models and image providers, selected by config.

Keeping selection here means agents just call ``get_chat_model()`` and stay
provider-agnostic. Swap Gemini/Groq (or a paid model later) via env only. When
the configured provider has no API key, we transparently fall back to a
deterministic mock so local dev / tests work without any keys.
"""
from __future__ import annotations

import os
from functools import lru_cache
from typing import TYPE_CHECKING

from app.agents.llm.images import ImageProvider, build_image_provider
from app.core.config import settings

if TYPE_CHECKING:
    from langchain_core.language_models.chat_models import BaseChatModel


def effective_text_provider(provider: str | None = None) -> str:
    """Resolve the text provider, falling back to 'mock' when the key is absent."""
    provider = provider or settings.llm_text_provider
    if provider == "gemini" and not settings.gemini_api_key:
        return "mock"
    if provider == "groq" and not settings.groq_api_key:
        return "mock"
    return provider


def effective_image_provider(name: str | None = None) -> str:
    name = name or settings.llm_image_provider
    # Avoid network in tests; mock unless a real key-backed provider is forced.
    if os.getenv("PYTEST_VERSION") is not None and name != "gemini":
        return "mock"
    if name == "gemini" and not settings.gemini_api_key:
        return "mock"
    return name


def get_chat_model(
    provider: str | None = None,
    *,
    temperature: float = 0.7,
    **kwargs,
) -> "BaseChatModel":
    """Return a configured LangChain chat model for the resolved provider."""
    provider = effective_text_provider(provider)

    if provider == "mock":
        from app.agents.llm.mock import MockChatModel

        return MockChatModel()

    if provider == "gemini":
        from langchain_google_genai import ChatGoogleGenerativeAI

        return ChatGoogleGenerativeAI(
            model=settings.gemini_text_model,
            google_api_key=settings.gemini_api_key,
            temperature=temperature,
            **kwargs,
        )

    if provider == "groq":
        from langchain_groq import ChatGroq

        return ChatGroq(
            model=settings.groq_model,
            api_key=settings.groq_api_key,
            temperature=temperature,
            **kwargs,
        )

    raise ValueError(f"Unknown text provider: {provider}")


@lru_cache
def get_image_provider(name: str | None = None) -> ImageProvider:
    return build_image_provider(effective_image_provider(name))
