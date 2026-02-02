"""LLM integration for smart routing and report generation."""

from app.llm.vertex_ai import VertexAIRouter, create_routing_tools

__all__ = ["VertexAIRouter", "create_routing_tools"]
