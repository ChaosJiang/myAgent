"""LangGraph state schema."""

from enum import Enum
from typing import TypedDict


class ActionType(str, Enum):
    """Possible next actions for the agent."""

    ASK_USER = "ask_user"
    CALL_FUNNEL = "call_funnel"
    CALL_COHORT = "call_cohort"
    ANSWER_CONTEXT = "answer_context"
    END = "end"


class Message(TypedDict):
    """Conversation message."""

    role: str  # 'user' or 'assistant'
    content: str
    timestamp: str


class AgentState(TypedDict):
    """State maintained throughout the conversation."""

    # Conversation
    session_id: str
    messages: list[Message]

    # Parameters
    parameters: dict | None
    missing_params: list[str]

    # Analysis results
    funnel_id: str | None
    funnel_result: dict | None  # FunnelAnalysisResponse as dict
    cohort_result: dict | None  # CohortAnalysisResponse as dict

    # Output
    report: dict | None  # Structured report
    next_action: str  # ActionType value

    # Metadata
    error: str | None
