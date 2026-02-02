"""Cohort analysis API client with retry logic."""

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from app.config import settings
from app.models import CohortParameters, CohortAnalysisResponse


class CohortAPIError(Exception):
    """Exception raised when cohort API calls fail."""

    pass


class CohortAPIClient:
    """Client for interacting with the cohort analysis API."""

    def __init__(self, base_url: str | None = None, timeout: int | None = None):
        """
        Initialize the cohort API client.

        Args:
            base_url: Override the base URL from settings
            timeout: Override the timeout from settings
        """
        self.base_url = base_url or settings.funnel_api_base_url
        self.timeout = timeout or settings.funnel_api_timeout

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((httpx.TimeoutException, httpx.NetworkError)),
        reraise=True,
    )
    async def analyze_cohort(self, params: CohortParameters) -> CohortAnalysisResponse:
        """
        Call the cohort analysis API with automatic retry.

        Args:
            params: Cohort analysis parameters (funnel_id, step_index)

        Returns:
            CohortAnalysisResponse with user characteristics comparison

        Raises:
            CohortAPIError: If the API returns an error after all retries
            httpx.TimeoutException: If all retry attempts timeout
            httpx.NetworkError: If network errors persist after retries
        """
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                response = await client.post(
                    f"{self.base_url}/cohort-analysis",
                    json={"funnel_id": params.funnel_id, "step_index": params.step_index},
                )
                response.raise_for_status()
                data = response.json()
                return CohortAnalysisResponse(**data)

            except httpx.HTTPStatusError as e:
                raise CohortAPIError(
                    f"Cohort API returned error {e.response.status_code}: {e.response.text}"
                ) from e
