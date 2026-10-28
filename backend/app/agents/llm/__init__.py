"""Pluggable, free-tier-first LLM layer.

Text agents use a LangChain chat model (so LangGraph can consume it directly);
image generation uses a small async provider interface. Both are selected by
config so paid providers can be swapped in without touching agent code.
"""
from app.agents.llm.factory import get_chat_model, get_image_provider

__all__ = ["get_chat_model", "get_image_provider"]
