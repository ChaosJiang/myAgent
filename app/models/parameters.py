"""Parameter models for funnel and cohort analysis."""

from datetime import datetime
from pydantic import BaseModel, Field


class FunnelParameters(BaseModel):
    """Parameters for funnel analysis API."""

    start_date: datetime = Field(description="Analysis start date")
    end_date: datetime = Field(description="Analysis end date")
    funnel_steps: list[str] = Field(
        min_length=2, description="Event names in funnel order (e.g., ['signup', 'verify_email'])"
    )
    user_segment: str | None = Field(
        None, description="User segment filter (e.g., 'mobile_users', 'premium_tier')"
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "start_date": "2026-01-01T00:00:00Z",
                    "end_date": "2026-01-31T23:59:59Z",
                    "funnel_steps": ["signup", "verify_email", "first_purchase"],
                    "user_segment": "new_users",
                }
            ]
        }
    }


class CohortParameters(BaseModel):
    """Parameters for cohort analysis API."""

    funnel_id: str = Field(description="Funnel ID from previous funnel analysis")
    step_index: int = Field(ge=0, description="0-based index of the step to analyze")

    model_config = {
        "json_schema_extra": {"examples": [{"funnel_id": "fnl_abc123xyz", "step_index": 1}]}
    }
