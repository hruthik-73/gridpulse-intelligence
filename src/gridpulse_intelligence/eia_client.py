"""Client for the U.S. Energy Information Administration API."""

from typing import Final

import httpx
import structlog
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from gridpulse_intelligence.config import get_settings
from gridpulse_intelligence.models import GridRegionRecord

logger = structlog.get_logger(__name__)

Record = dict[str, object]


class EIAError(Exception):
    """Base exception for EIA API failures."""


class EIATransientError(EIAError):
    """Temporary EIA API failure that may succeed after retrying."""


class EIAClient:
    """HTTP client for EIA API v2."""

    BASE_URL: Final[str] = "https://api.eia.gov/v2"

    def __init__(self, timeout_seconds: float = 20.0) -> None:
        """Initialize the EIA API client."""
        settings = get_settings()

        self._api_key = settings.eia_api_key.get_secret_value()

        self._client = httpx.Client(
            base_url=self.BASE_URL,
            timeout=httpx.Timeout(timeout_seconds),
            headers={
                "Accept": "application/json",
                "User-Agent": "GridPulse-Intelligence/0.1",
            },
        )

    def close(self) -> None:
        """Close the underlying HTTP connection pool."""
        self._client.close()

    @retry(
        retry=retry_if_exception_type(EIATransientError),
        stop=stop_after_attempt(4),
        wait=wait_exponential(
            multiplier=1,
            min=1,
            max=8,
        ),
        reraise=True,
    )
    def _request(
        self,
        endpoint: str,
        params: dict[str, str],
    ) -> Record:
        """Send a request to the EIA API."""

        request_params: dict[str, str] = {
            "api_key": self._api_key,
            **params,
        }

        logger.info(
            "eia_request_started",
            endpoint=endpoint,
        )

        try:
            response = self._client.get(
                endpoint,
                params=request_params,
            )
        except httpx.RequestError:
            logger.warning(
                "eia_network_error",
                endpoint=endpoint,
            )
            raise EIATransientError("Network error while contacting the EIA API.") from None

        if response.status_code == 429 or response.status_code >= 500:
            logger.warning(
                "eia_transient_error",
                endpoint=endpoint,
                status_code=response.status_code,
            )
            raise EIATransientError(
                f"EIA API temporarily unavailable. Status: {response.status_code}"
            )

        if response.status_code >= 400:
            logger.error(
                "eia_request_failed",
                endpoint=endpoint,
                status_code=response.status_code,
            )
            raise EIAError(f"EIA API request failed. Status: {response.status_code}")

        try:
            payload: object = response.json()
        except ValueError:
            raise EIAError("EIA API returned invalid JSON.") from None

        if not isinstance(payload, dict):
            raise EIAError("Unexpected EIA API response format.")

        logger.info(
            "eia_request_completed",
            endpoint=endpoint,
            status_code=response.status_code,
        )

        return {str(key): value for key, value in payload.items()}

    def get_latest_region_data(
        self,
        length: int = 5,
    ) -> list[GridRegionRecord]:
        """Return validated latest hourly EIA regional grid records."""

        if not 1 <= length <= 5000:
            raise ValueError("length must be between 1 and 5000")

        payload = self._request(
            endpoint="/electricity/rto/region-data/data/",
            params={
                "frequency": "hourly",
                "data[0]": "value",
                "sort[0][column]": "period",
                "sort[0][direction]": "desc",
                "offset": "0",
                "length": str(length),
            },
        )

        response_section = payload.get("response")

        if not isinstance(response_section, dict):
            raise EIAError("EIA response is missing the response section.")

        records = response_section.get("data")

        if not isinstance(records, list):
            raise EIAError("EIA response is missing the data section.")

        result: list[GridRegionRecord] = []

        for record in records:
            if isinstance(record, dict):
                normalized_record = {str(key): value for key, value in record.items()}

                validated_record = GridRegionRecord.model_validate(normalized_record)

                result.append(validated_record)

        logger.info(
            "eia_records_received",
            record_count=len(result),
        )

        return result
