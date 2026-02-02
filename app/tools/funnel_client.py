"""Funnel analysis API client with retry logic."""

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from app.config import settings
from app.models import FunnelParameters, FunnelAnalysisResponse


class FunnelAPIError(Exception):
    """Exception raised when funnel API calls fail."""

    pass


class FunnelAPIClient:
    """Client for interacting with the funnel analysis API."""

    def __init__(self, base_url: str | None = None, timeout: int | None = None):
        """
        Initialize the funnel API client.

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
    async def analyze_funnel(self, params: FunnelParameters) -> FunnelAnalysisResponse:
        """
        Call the funnel analysis API with automatic retry.

        Args:
            params: Funnel analysis parameters

        Returns:
            FunnelAnalysisResponse with funnel_id and analysis results

        Raises:
            FunnelAPIError: If the API returns an error after all retries
            httpx.TimeoutException: If all retry attempts timeout
            httpx.NetworkError: If network errors persist after retries
        """
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                response = await client.post(
                    f"{self.base_url}/funnel-analysis",
                    json={
                        "start_date": params.start_date.isoformat(),
                        "end_date": params.end_date.isoformat(),
                        "funnel_steps": params.funnel_steps,
                        "user_segment": params.user_segment,
                    },
                )
                response.raise_for_status()
                data = response.json()
                return FunnelAnalysisResponse(**data)

            except httpx.HTTPStatusError as e:
                raise FunnelAPIError(
                    f"Funnel API returned error {e.response.status_code}: {e.response.text}"
                ) from e
