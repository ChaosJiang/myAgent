"""Response models for APIs and chat endpoints."""

from datetime import datetime
from pydantic import BaseModel, Field


# Funnel Analysis Models
class FunnelStep(BaseModel):
    """Individual step in a funnel."""

    step_index: int
    name: str
    users: int
    conversion_rate: float
    drop_off: int | None = None


class DateRange(BaseModel):
    """Date range for analysis."""

    start: str
    end: str


class FunnelAnalysisResponse(BaseModel):
    """Response from funnel analysis API."""

    funnel_id: str
    steps: list[FunnelStep]
    overall_conversion: float
    total_users: int
    date_range: DateRange


# Cohort Analysis Models
class CohortCharacteristics(BaseModel):
    """User cohort characteristics."""

    count: int
    characteristics: dict[str, float | list | dict] = Field(
        description="Demographics, behavior patterns, etc."
    )


class CohortInsights(BaseModel):
    """Insights from cohort comparison."""

    key_differences: list[str]


class CohortAnalysisResponse(BaseModel):
    """Response from cohort analysis API."""

    step_name: str
    step_index: int
    converted: CohortCharacteristics
    dropped: CohortCharacteristics
    insights: CohortInsights


# Chat API Models
class ChatRequest(BaseModel):
    """Request to chat endpoint."""

    session_id: str = Field(description="Unique session identifier for conversation continuity")
    message: str = Field(description="User's message")


class ChatResponse(BaseModel):
    """Response from chat endpoint."""

    session_id: str
    response: str = Field(description="Agent's response message")
    needs_input: bool = Field(description="Whether the agent needs more information from the user")
    missing_params: list[str] = Field(
        default_factory=list, description="List of missing parameters"
    )
    metadata: dict = Field(
        default_factory=dict,
        description="Additional metadata (action_taken, funnel_id, etc.)",
    )
