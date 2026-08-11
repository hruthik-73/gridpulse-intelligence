"""Client for the U.S. Energy Information Administration API."""

from datetime import datetime
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
    MAX_PAGE_SIZE: Final[int] = 5000
    REGION_DATA_ENDPOINT: Final[str] = "/electricity/rto/region-data/data/"

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

    @staticmethod
    def _extract_response(
        payload: Record,
    ) -> tuple[list[Record], int]:
        """Extract records and total row count from an EIA response."""

        response_section = payload.get("response")

        if not isinstance(response_section, dict):
            raise EIAError("EIA response is missing the response section.")

        raw_records = response_section.get("data")
        raw_total = response_section.get("total")

        if not isinstance(raw_records, list):
            raise EIAError("EIA response is missing the data section.")

        if not isinstance(raw_total, str):
            raise EIAError("EIA response is missing the total row count.")

        try:
            total = int(raw_total)
        except ValueError:
            raise EIAError("EIA response total row count is invalid.") from None

        records: list[Record] = []

        for record in raw_records:
            if isinstance(record, dict):
                records.append({str(key): value for key, value in record.items()})

        return records, total

    @staticmethod
    def _validate_records(
        records: list[Record],
    ) -> list[GridRegionRecord]:
        """Convert raw EIA records into validated GridRegionRecord objects."""

        return [GridRegionRecord.model_validate(record) for record in records]

    def get_latest_region_data(
        self,
        length: int = 5,
    ) -> list[GridRegionRecord]:
        """Return the latest validated hourly EIA regional grid records."""

        if not 1 <= length <= self.MAX_PAGE_SIZE:
            raise ValueError(f"length must be between 1 and {self.MAX_PAGE_SIZE}")

        payload = self._request(
            endpoint=self.REGION_DATA_ENDPOINT,
            params={
                "frequency": "hourly",
                "data[0]": "value",
                "sort[0][column]": "period",
                "sort[0][direction]": "desc",
                "sort[1][column]": "respondent",
                "sort[1][direction]": "asc",
                "sort[2][column]": "type",
                "sort[2][direction]": "asc",
                "offset": "0",
                "length": str(length),
            },
        )

        raw_records, _ = self._extract_response(payload)

        records = self._validate_records(raw_records)

        logger.info(
            "eia_records_received",
            record_count=len(records),
        )

        return records

    def get_region_data(
        self,
        start: datetime,
        end: datetime,
        page_size: int = 5000,
        max_records: int | None = None,
    ) -> list[GridRegionRecord]:
        """Retrieve historical EIA regional data using pagination."""

        if start > end:
            raise ValueError("start must be earlier than or equal to end")

        if not 1 <= page_size <= self.MAX_PAGE_SIZE:
            raise ValueError(f"page_size must be between 1 and {self.MAX_PAGE_SIZE}")

        if max_records is not None and max_records < 1:
            raise ValueError("max_records must be greater than zero")

        start_value = start.strftime("%Y-%m-%dT%H")
        end_value = end.strftime("%Y-%m-%dT%H")

        offset = 0
        total_available: int | None = None
        results: list[GridRegionRecord] = []

        while True:
            remaining = None if max_records is None else max_records - len(results)

            if remaining is not None and remaining <= 0:
                break

            current_page_size = page_size if remaining is None else min(page_size, remaining)

            logger.info(
                "eia_page_requested",
                offset=offset,
                page_size=current_page_size,
                start=start_value,
                end=end_value,
            )

            payload = self._request(
                endpoint=self.REGION_DATA_ENDPOINT,
                params={
                    "frequency": "hourly",
                    "data[0]": "value",
                    "start": start_value,
                    "end": end_value,
                    "sort[0][column]": "period",
                    "sort[0][direction]": "asc",
                    "sort[1][column]": "respondent",
                    "sort[1][direction]": "asc",
                    "sort[2][column]": "type",
                    "sort[2][direction]": "asc",
                    "offset": str(offset),
                    "length": str(current_page_size),
                },
            )

            raw_records, total_available = self._extract_response(payload)

            if not raw_records:
                break

            validated_records = self._validate_records(raw_records)

            results.extend(validated_records)

            logger.info(
                "eia_page_received",
                offset=offset,
                records_received=len(validated_records),
                records_collected=len(results),
                total_available=total_available,
            )

            offset += len(raw_records)

            if offset >= total_available:
                break

        logger.info(
            "eia_pagination_completed",
            records_collected=len(results),
            total_available=total_available,
            start=start_value,
            end=end_value,
        )

        return results
