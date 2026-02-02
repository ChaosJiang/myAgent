"""LLM integration for smart routing and report generation."""

from app.llm.openai_router import OpenAIRouter, get_routing_tools

__all__ = ["OpenAIRouter", "get_routing_tools"]
