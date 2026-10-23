
from pydantic import ValidationError

from typing import Any

from datetime import datetime
import httpx

from app.config import settings
from app.schemas.sam_gov import SamOpportunitySearchResponse
from app.services.http_errors import translate_http_error
from app.utils.exceptions import AppException

"""Client for the official SAM.gov Opportunities Public API."""

SAM_API_BASE_URL = "https://api.sam.gov/opportunities/v2/search"


class SamGovClient:
    """Make authenticated requests to the official SAM.gov API."""



    def __init__(
        self,
        api_key: str | None = None,
        timeout_seconds: float = 20.0,
    ) -> None:
        if timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be greater than zero")

        self._api_key = api_key or settings.SAM_API_KEY
        self._timeout_seconds = timeout_seconds




    @staticmethod
    def _validate_date_window(
        posted_from: str,
        posted_to: str,
    ) -> None:
        """Validate SAM.gov date format and maximum date window."""
        try:
            start_date = datetime.strptime(
                posted_from, "%m/%d/%Y"
            ).date()
            end_date = datetime.strptime(
                posted_to, "%m/%d/%Y"
            ).date()
        except ValueError as exc:
            raise ValueError(
                "Dates must use MM/DD/YYYY format."
            ) from exc

        if start_date > end_date:
            raise ValueError(
                "posted_from must be on or before posted_to."
            )

        if (end_date - start_date).days > 365:
            raise ValueError(
                "The date window must not exceed 365 days."
            )

    def search_opportunities(
        self,
        *,
        posted_from: str,
        posted_to: str,
        limit: int = 100,
        offset: int = 0,
    ) -> dict[str, Any]:
        """Fetch and validate one bounded page of opportunities."""
        self._validate_date_window(posted_from, posted_to)

        if not 1 <= limit <= 1000:
            raise ValueError("limit must be between 1 and 1000")
        if offset < 0:
            raise ValueError("offset must be non-negative")

        params = {
            "api_key": self._api_key,
            "postedFrom": posted_from,
            "postedTo": posted_to,
            "limit": limit,
            "offset": offset,
        }

        try:
            with httpx.Client(timeout=self._timeout_seconds) as client:
                response = client.get(SAM_API_BASE_URL, params=params)
                response.raise_for_status()
                payload = response.json()

        except httpx.HTTPError as exc:
            raise translate_http_error(exc) from exc
        except ValueError as exc:
            raise AppException(
                detail="SAM.gov returned an invalid response.",
                status_code=502,
                code="EXTERNAL_SERVICE_INVALID_RESPONSE",
            ) from exc

        try:
            validated = SamOpportunitySearchResponse.model_validate(payload)
        except ValidationError as exc:
            raise AppException(
                detail="SAM.gov returned an invalid response.",
                status_code=502,
                code="EXTERNAL_SERVICE_INVALID_RESPONSE",
            ) from exc

        return validated.model_dump(by_alias=False)
