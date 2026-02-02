"""Vertex AI integration with function calling for smart routing."""

import json
from datetime import datetime
from typing import Any

import vertexai
from vertexai.generative_models import (
    FunctionDeclaration,
    GenerativeModel,
    Tool,
    Content,
    Part,
)

from app.config import settings


def create_routing_tools() -> Tool:
    """
    Create Vertex AI function declarations for smart routing.

    Returns:
        Tool object with function declarations for analyze_funnel, analyze_cohort, answer_from_memory
    """
    analyze_funnel = FunctionDeclaration(
        name="analyze_funnel",
        description="Run a new funnel analysis with specified date range, funnel steps, and optional user segment",
        parameters={
            "type": "object",
            "properties": {
                "start_date": {
                    "type": "string",
                    "description": "Start date in ISO format (YYYY-MM-DD or YYYY-MM-DDTHH:MM:SSZ)",
                },
                "end_date": {
                    "type": "string",
                    "description": "End date in ISO format (YYYY-MM-DD or YYYY-MM-DDTHH:MM:SSZ)",
                },
                "funnel_steps": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Event names in funnel order (minimum 2 steps)",
                },
                "user_segment": {
                    "type": "string",
                    "description": "Optional user segment filter (e.g., 'mobile_users', 'premium_tier')",
                },
            },
            "required": ["start_date", "end_date", "funnel_steps"],
        },
    )

    analyze_cohort = FunctionDeclaration(
        name="analyze_cohort",
        description="Deep-dive into a specific funnel step to understand user cohort characteristics (converted vs dropped users)",
        parameters={
            "type": "object",
            "properties": {
                "step_index": {
                    "type": "integer",
                    "description": "0-based index of the funnel step to analyze in detail",
                }
            },
            "required": ["step_index"],
        },
    )

    answer_from_memory = FunctionDeclaration(
        name="answer_from_memory",
        description="Answer the user's question using existing funnel or cohort analysis results without making new API calls",
        parameters={
            "type": "object",
            "properties": {
                "answer": {
                    "type": "string",
                    "description": "The answer to the user's question based on existing data",
                },
                "reasoning": {
                    "type": "string",
                    "description": "Why existing data is sufficient to answer this question",
                },
            },
            "required": ["answer", "reasoning"],
        },
    )

    return Tool(function_declarations=[analyze_funnel, analyze_cohort, answer_from_memory])


class VertexAIRouter:
    """Smart router using Vertex AI for decision making."""

    def __init__(self, project_id: str | None = None, location: str | None = None):
        """
        Initialize Vertex AI router.

        Args:
            project_id: GCP project ID (defaults to settings)
            location: GCP location (defaults to settings)
        """
        self.project_id = project_id or settings.gcp_project_id
        self.location = location or settings.gcp_location

        # Initialize Vertex AI
        vertexai.init(project=self.project_id, location=self.location)

        # Create model with routing tools
        self.model = GenerativeModel(settings.vertex_ai_model, tools=[create_routing_tools()])

    async def route_request(
        self,
        user_message: str,
        funnel_id: str | None,
        funnel_result: dict | None,
        cohort_result: dict | None,
    ) -> tuple[str, dict[str, Any]]:
        """
        Use LLM to decide the next action: call API or answer from context.

        Args:
            user_message: User's latest message
            funnel_id: Current funnel ID (if available)
            funnel_result: Previous funnel analysis result (if available)
            cohort_result: Previous cohort analysis result (if available)

        Returns:
            Tuple of (action_name, parameters)
            - action_name: "analyze_funnel", "analyze_cohort", or "answer_from_memory"
            - parameters: Dict of function arguments
        """
        # Build context for the LLM
        context = self._build_context(user_message, funnel_id, funnel_result, cohort_result)

        # Generate response with function calling
        response = await self.model.generate_content_async(
            context,
            generation_config={"temperature": 0.1},  # Low temp for consistent routing
        )

        # Extract function call
        if not response.candidates:
            raise ValueError("No response from Vertex AI")

        candidate = response.candidates[0]
        if not candidate.content.parts:
            raise ValueError("No content parts in response")

        # Get the function call
        function_call = None
        for part in candidate.content.parts:
            if part.function_call:
                function_call = part.function_call
                break

        if not function_call:
            # Fallback: answer from memory with the text response
            return "answer_from_memory", {
                "answer": candidate.content.text
                if candidate.content.text
                else "I don't have enough information to answer that.",
                "reasoning": "No specific action needed",
            }

        # Extract function name and args
        action_name = function_call.name
        parameters = dict(function_call.args)

        return action_name, parameters

    def _build_context(
        self,
        user_message: str,
        funnel_id: str | None,
        funnel_result: dict | None,
        cohort_result: dict | None,
    ) -> str:
        """Build context string for the LLM."""
        context_parts = [
            "You are an intelligent routing agent for funnel analysis. Your job is to decide the best action to fulfill the user's request.\n",
            f"Current state:",
            f"- Funnel ID: {funnel_id or 'None'}",
            f"- Funnel result available: {bool(funnel_result)}",
            f"- Cohort result available: {bool(cohort_result)}",
            "",
        ]

        if funnel_result:
            context_parts.extend(
                [
                    "Previous funnel analysis:",
                    json.dumps(funnel_result, indent=2),
                    "",
                ]
            )

        if cohort_result:
            context_parts.extend(
                [
                    "Previous cohort analysis:",
                    json.dumps(cohort_result, indent=2),
                    "",
                ]
            )

        context_parts.extend(
            [
                f'User\'s message: "{user_message}"',
                "",
                "Instructions:",
                "1. If the user is asking for a NEW funnel analysis (different dates, steps, or segment), call analyze_funnel",
                "2. If the user wants to understand WHY users drop off at a specific step, call analyze_cohort",
                "3. If the question can be answered with existing data, use answer_from_memory",
                "4. For ambiguous requests, prefer answer_from_memory if data exists",
                "",
                "Choose the appropriate function to call.",
            ]
        )

        return "\n".join(context_parts)

    async def generate_report(
        self, funnel_result: dict | None = None, cohort_result: dict | None = None
    ) -> dict:
        """
        Generate structured report from analysis results.

        Args:
            funnel_result: Funnel analysis data
            cohort_result: Cohort analysis data

        Returns:
            Structured report with overview, metrics, insights, recommendations
        """
        if not funnel_result and not cohort_result:
            raise ValueError("At least one result (funnel or cohort) must be provided")

        # Build prompt for report generation
        prompt_parts = [
            "Generate a structured funnel analysis report based on the following data:\n"
        ]

        if funnel_result:
            prompt_parts.extend(
                [
                    "Funnel Analysis Results:",
                    json.dumps(funnel_result, indent=2),
                    "",
                ]
            )

        if cohort_result:
            prompt_parts.extend(
                [
                    "Cohort Analysis Results:",
                    json.dumps(cohort_result, indent=2),
                    "",
                ]
            )

        prompt_parts.extend(
            [
                "Please provide a structured report with the following sections:",
                "1. Overview: High-level summary of the funnel/analysis",
                "2. Metrics: Key numbers and conversion rates",
                "3. Insights: 3-5 actionable insights from the data",
                "4. Recommendations: 2-3 specific recommendations for improvement",
                "",
                "Format the response as a JSON object with these keys: overview, metrics, insights (array), recommendations (array)",
            ]
        )

        # Generate without function calling
        model_plain = GenerativeModel(settings.vertex_ai_model)
        response = await model_plain.generate_content_async(
            "\n".join(prompt_parts),
            generation_config={
                "temperature": 0.3,
                "response_mime_type": "application/json",
            },
        )

        # Parse JSON response
        try:
            report = json.loads(response.text)
            return report
        except json.JSONDecodeError:
            # Fallback structure if JSON parsing fails
            return {
                "overview": response.text[:500],
                "metrics": {},
                "insights": ["Failed to parse detailed insights"],
                "recommendations": ["Review the analysis data manually"],
            }
