"""Mock API server for testing myAgent without real funnel/cohort APIs."""

import random
import uuid
from datetime import datetime, timedelta
from typing import List

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field


app = FastAPI(
    title="Mock Funnel API",
    description="Mock server for testing myAgent",
    version="1.0.0",
)


class FunnelRequest(BaseModel):
    start_date: str
    end_date: str
    funnel_steps: List[str] = Field(min_length=2)
    user_segment: str | None = None


class FunnelStep(BaseModel):
    step_index: int
    name: str
    users: int
    conversion_rate: float
    drop_off: int | None = None


class DateRange(BaseModel):
    start: str
    end: str


class FunnelResponse(BaseModel):
    funnel_id: str
    steps: List[FunnelStep]
    overall_conversion: float
    total_users: int
    date_range: DateRange


class CohortRequest(BaseModel):
    funnel_id: str
    step_index: int = Field(ge=0)


class CohortCharacteristics(BaseModel):
    count: int
    characteristics: dict


class CohortInsights(BaseModel):
    key_differences: List[str]


class CohortResponse(BaseModel):
    step_name: str
    step_index: int
    converted: CohortCharacteristics
    dropped: CohortCharacteristics
    insights: CohortInsights


funnel_cache = {}


def generate_mock_funnel_data(
    funnel_steps: List[str], total_users: int = 10000
) -> tuple[List[FunnelStep], float]:
    """Generate realistic mock funnel data."""
    steps = []
    current_users = total_users

    for idx, step_name in enumerate(funnel_steps):
        if idx == 0:
            conversion_rate = 100.0
            drop_off = None
        else:
            conversion_rate = random.uniform(60, 85)
            next_users = int(current_users * (conversion_rate / 100))
            drop_off = current_users - next_users
            current_users = next_users

        steps.append(
            FunnelStep(
                step_index=idx,
                name=step_name,
                users=current_users,
                conversion_rate=conversion_rate,
                drop_off=drop_off,
            )
        )

        if idx > 0:
            current_users = int(current_users * (random.uniform(0.65, 0.85)))

    overall_conversion = (current_users / total_users) * 100
    return steps, overall_conversion


def generate_mock_cohort_data(step_name: str, step_index: int) -> CohortResponse:
    """Generate realistic mock cohort analysis data."""

    converted_count = random.randint(5000, 8000)
    dropped_count = random.randint(2000, 4000)

    converted = CohortCharacteristics(
        count=converted_count,
        characteristics={
            "avg_age": round(random.uniform(25, 32), 1),
            "top_countries": ["US", "UK", "CA"],
            "device_split": {
                "mobile": random.randint(60, 75),
                "desktop": random.randint(25, 40),
            },
            "avg_session_time": f"{random.uniform(5, 12):.1f} minutes",
        },
    )

    dropped = CohortCharacteristics(
        count=dropped_count,
        characteristics={
            "avg_age": round(random.uniform(28, 35), 1),
            "top_countries": ["US", "IN", "BR"],
            "device_split": {
                "mobile": random.randint(40, 55),
                "desktop": random.randint(45, 60),
            },
            "avg_session_time": f"{random.uniform(1, 4):.1f} minutes",
        },
    )

    insights = CohortInsights(
        key_differences=[
            f"Dropped users spent {random.randint(60, 80)}% less time on the page",
            f"Desktop users have higher drop-off rate ({random.randint(18, 25)}% vs {random.randint(10, 15)}%)",
            "Users from India and Brazil have 3x higher drop-off",
            f"Converted users are on average {abs(converted.characteristics['avg_age'] - dropped.characteristics['avg_age']):.1f} years younger",
        ]
    )

    return CohortResponse(
        step_name=step_name,
        step_index=step_index,
        converted=converted,
        dropped=dropped,
        insights=insights,
    )


@app.get("/")
async def root():
    return {
        "name": "Mock Funnel API",
        "version": "1.0.0",
        "endpoints": ["/api/funnel-analysis", "/api/cohort-analysis"],
    }


@app.post("/api/funnel-analysis", response_model=FunnelResponse)
async def funnel_analysis(request: FunnelRequest):
    """
    Mock funnel analysis endpoint.

    Returns realistic conversion funnel data with random but consistent values.
    """

    funnel_id = f"fnl_{uuid.uuid4().hex[:12]}"

    steps, overall_conversion = generate_mock_funnel_data(request.funnel_steps)

    response = FunnelResponse(
        funnel_id=funnel_id,
        steps=steps,
        overall_conversion=round(overall_conversion, 2),
        total_users=steps[0].users,
        date_range=DateRange(
            start=request.start_date.split("T")[0],
            end=request.end_date.split("T")[0],
        ),
    )

    funnel_cache[funnel_id] = {
        "steps": request.funnel_steps,
        "response": response,
    }

    return response


@app.post("/api/cohort-analysis", response_model=CohortResponse)
async def cohort_analysis(request: CohortRequest):
    """
    Mock cohort analysis endpoint.

    Returns comparison of converted vs dropped users at a specific funnel step.
    """

    if request.funnel_id not in funnel_cache:
        raise HTTPException(
            status_code=404,
            detail=f"Funnel ID '{request.funnel_id}' not found. Run funnel analysis first.",
        )

    funnel_data = funnel_cache[request.funnel_id]
    steps = funnel_data["steps"]

    if request.step_index >= len(steps):
        raise HTTPException(
            status_code=400,
            detail=f"Invalid step_index {request.step_index}. Funnel has {len(steps)} steps (0-{len(steps) - 1}).",
        )

    step_name = steps[request.step_index]

    return generate_mock_cohort_data(step_name, request.step_index)


@app.get("/health")
async def health():
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}


if __name__ == "__main__":
    import uvicorn

    print("🚀 Starting Mock Funnel API Server...")
    print("📍 Funnel Analysis: http://localhost:8080/api/funnel-analysis")
    print("📍 Cohort Analysis: http://localhost:8080/api/cohort-analysis")
    print("📍 Health Check: http://localhost:8080/health")

    uvicorn.run("mock_server:app", host="0.0.0.0", port=8080, reload=True)
