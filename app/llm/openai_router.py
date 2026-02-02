"""OpenAI integration with function calling for smart routing."""

import json
from typing import Any

from openai import AsyncOpenAI

from app.config import settings


def get_routing_tools() -> list[dict]:
    """
    Create OpenAI function definitions for smart routing.

    Returns:
        List of tool definitions for analyze_funnel, analyze_cohort, answer_from_memory
    """
    return [
        {
            "type": "function",
            "function": {
                "name": "analyze_funnel",
                "description": "Run a new funnel analysis with specified date range, funnel steps, and optional user segment",
                "parameters": {
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
            },
        },
        {
            "type": "function",
            "function": {
                "name": "analyze_cohort",
                "description": "Deep-dive into a specific funnel step to understand user cohort characteristics (converted vs dropped users)",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "step_index": {
                            "type": "integer",
                            "description": "0-based index of the funnel step to analyze in detail",
                        }
                    },
                    "required": ["step_index"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "answer_from_memory",
                "description": "Answer the user's question using existing funnel or cohort analysis results without making new API calls",
                "parameters": {
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
            },
        },
    ]


class OpenAIRouter:
    """Smart router using OpenAI for decision making."""

    def __init__(self, api_key: str | None = None):
        """
        Initialize OpenAI router.

        Args:
            api_key: OpenAI API key (defaults to settings)
        """
        self.client = AsyncOpenAI(api_key=api_key or settings.openai_api_key)
        self.model = settings.openai_model

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
        messages = self._build_messages(user_message, funnel_id, funnel_result, cohort_result)

        response = await self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            tools=get_routing_tools(),
            tool_choice="auto",
            temperature=0.1,
        )

        choice = response.choices[0]

        if choice.message.tool_calls:
            tool_call = choice.message.tool_calls[0]
            action_name = tool_call.function.name
            parameters = json.loads(tool_call.function.arguments)
            return action_name, parameters

        return "answer_from_memory", {
            "answer": choice.message.content or "I don't have enough information to answer that.",
            "reasoning": "No specific action needed",
        }

    def _build_messages(
        self,
        user_message: str,
        funnel_id: str | None,
        funnel_result: dict | None,
        cohort_result: dict | None,
    ) -> list[dict]:
        """Build message list for the LLM."""
        system_content = """You are an intelligent routing agent for funnel analysis. Your job is to decide the best action to fulfill the user's request.

Instructions:
1. If the user is asking for a NEW funnel analysis (different dates, steps, or segment), call analyze_funnel
2. If the user wants to understand WHY users drop off at a specific step, call analyze_cohort
3. If the question can be answered with existing data, use answer_from_memory
4. For ambiguous requests, prefer answer_from_memory if data exists

Choose the appropriate function to call."""

        context_parts = [
            f"Current state:",
            f"- Funnel ID: {funnel_id or 'None'}",
            f"- Funnel result available: {bool(funnel_result)}",
            f"- Cohort result available: {bool(cohort_result)}",
        ]

        if funnel_result:
            context_parts.extend(
                [
                    "",
                    "Previous funnel analysis:",
                    json.dumps(funnel_result, indent=2),
                ]
            )

        if cohort_result:
            context_parts.extend(
                [
                    "",
                    "Previous cohort analysis:",
                    json.dumps(cohort_result, indent=2),
                ]
            )

        user_content = "\n".join(context_parts) + f'\n\nUser\'s message: "{user_message}"'

        return [
            {"role": "system", "content": system_content},
            {"role": "user", "content": user_content},
        ]

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

        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": "\n".join(prompt_parts)}],
            temperature=0.3,
            response_format={"type": "json_object"},
        )

        try:
            report = json.loads(response.choices[0].message.content)
            return report
        except json.JSONDecodeError:
            return {
                "overview": response.choices[0].message.content[:500],
                "metrics": {},
                "insights": ["Failed to parse detailed insights"],
                "recommendations": ["Review the analysis data manually"],
            }
