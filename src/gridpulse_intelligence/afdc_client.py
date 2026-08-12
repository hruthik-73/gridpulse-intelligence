"""Client for AFDC alternative fuel station data."""

from typing import Final

import httpx
import structlog
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from gridpulse_intelligence.config import get_settings
from gridpulse_intelligence.models import (
    EVChargingStationRecord,
)

logger = structlog.get_logger(__name__)

Record = dict[str, object]


class AFDCError(Exception):
    """Base exception for AFDC API failures."""


class AFDCTransientError(AFDCError):
    """Temporary AFDC API failure that may succeed after retrying."""


class AFDCClient:
    """Client for public EV charging infrastructure."""

    BASE_URL: Final[str] = "https://developer.nlr.gov"

    STATIONS_ENDPOINT: Final[str] = "/api/alt-fuel-stations/v1.json"

    MAX_LIMIT: Final[int] = 200

    def __init__(
        self,
        timeout_seconds: float = 20.0,
    ) -> None:
        settings = get_settings()

        if settings.afdc_api_key is None:
            raise AFDCError("AFDC_API_KEY is not configured.")

        api_key = settings.afdc_api_key.get_secret_value()

        self._client = httpx.Client(
            base_url=self.BASE_URL,
            timeout=httpx.Timeout(timeout_seconds),
            headers={
                "Accept": "application/json",
                "X-Api-Key": api_key,
                "User-Agent": ("GridPulse-Intelligence/0.1"),
            },
        )

    def close(self) -> None:
        """Close the underlying HTTP client."""

        self._client.close()

    @retry(
        retry=retry_if_exception_type(AFDCTransientError),
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
        params: dict[str, str],
    ) -> Record:
        """Request station data without logging credentials."""

        logger.info(
            "afdc_request_started",
            endpoint=self.STATIONS_ENDPOINT,
        )

        try:
            response = self._client.get(
                self.STATIONS_ENDPOINT,
                params=params,
            )
        except httpx.RequestError:
            logger.warning(
                "afdc_network_error",
                endpoint=self.STATIONS_ENDPOINT,
            )

            raise AFDCTransientError("Network error while contacting the AFDC API.") from None

        if response.status_code == 429 or response.status_code >= 500:
            logger.warning(
                "afdc_transient_error",
                endpoint=self.STATIONS_ENDPOINT,
                status_code=response.status_code,
            )

            raise AFDCTransientError(
                f"AFDC API temporarily unavailable. Status: {response.status_code}"
            )

        if response.status_code >= 400:
            logger.error(
                "afdc_request_failed",
                endpoint=self.STATIONS_ENDPOINT,
                status_code=response.status_code,
            )

            raise AFDCError(f"AFDC API request failed. Status: {response.status_code}")

        try:
            payload: object = response.json()
        except ValueError:
            raise AFDCError("AFDC API returned invalid JSON.") from None

        if not isinstance(payload, dict):
            raise AFDCError("Unexpected AFDC API response format.")

        logger.info(
            "afdc_request_completed",
            endpoint=self.STATIONS_ENDPOINT,
            status_code=response.status_code,
        )

        return {str(key): value for key, value in payload.items()}

    @staticmethod
    def _extract_response(
        payload: Record,
    ) -> tuple[list[Record], int]:
        """Extract station records and total result count."""

        raw_total = payload.get("total_results")

        if not isinstance(raw_total, int):
            raise AFDCError("AFDC response is missing total_results.")

        raw_stations = payload.get("fuel_stations")

        if not isinstance(raw_stations, list):
            raise AFDCError("AFDC response is missing fuel_stations.")

        stations: list[Record] = []

        for station in raw_stations:
            if not isinstance(station, dict):
                raise AFDCError("AFDC response contains an invalid station.")

            stations.append({str(key): value for key, value in station.items()})

        return stations, raw_total

    @staticmethod
    def _normalize_station(
        station: Record,
    ) -> EVChargingStationRecord:
        """Normalize one AFDC EV station."""

        raw_connectors = station.get("ev_connector_types")

        if raw_connectors is None:
            connectors: list[str] = []

        elif isinstance(raw_connectors, list):
            connectors = []

            for connector in raw_connectors:
                if not isinstance(
                    connector,
                    str,
                ):
                    raise AFDCError("AFDC station contains an invalid EV connector type.")

                connectors.append(connector)

        else:
            raise AFDCError("AFDC station contains invalid ev_connector_types.")

        try:
            return EVChargingStationRecord.model_validate(
                {
                    "station_id": station.get("id"),
                    "station_name": station.get("station_name"),
                    "street_address": station.get("street_address"),
                    "city": station.get("city"),
                    "state": station.get("state"),
                    "zip_code": station.get("zip"),
                    "country": station.get("country"),
                    "latitude": station.get("latitude"),
                    "longitude": station.get("longitude"),
                    "fuel_type_code": station.get("fuel_type_code"),
                    "access_code": station.get("access_code"),
                    "status_code": station.get("status_code"),
                    "ev_network": station.get("ev_network"),
                    "ev_connector_types": connectors,
                    "ev_level1_evse_num": station.get("ev_level1_evse_num"),
                    "ev_level2_evse_num": station.get("ev_level2_evse_num"),
                    "ev_dc_fast_num": station.get("ev_dc_fast_num"),
                    "facility_type": station.get("facility_type"),
                    "date_last_confirmed": station.get("date_last_confirmed"),
                    "updated_at": station.get("updated_at"),
                }
            )

        except ValueError as exc:
            station_id = station.get(
                "id",
                "unknown",
            )

            raise AFDCError(f"AFDC station failed validation. Station ID: {station_id}") from exc

    def get_public_ev_stations(
        self,
        state: str,
        limit: int = 50,
    ) -> tuple[
        list[EVChargingStationRecord],
        int,
    ]:
        """Return available public EV stations for a state."""

        normalized_state = state.strip().upper()

        if len(normalized_state) != 2 or not normalized_state.isalpha():
            raise ValueError("state must be a two-letter code")

        if not 1 <= limit <= self.MAX_LIMIT:
            raise ValueError(f"limit must be between 1 and {self.MAX_LIMIT}")

        payload = self._request(
            params={
                "fuel_type": "ELEC",
                "access": "public",
                "status": "E",
                "country": "US",
                "state": normalized_state,
                "limit": str(limit),
            }
        )

        raw_stations, total_results = self._extract_response(payload)

        records = [self._normalize_station(station) for station in raw_stations]

        records.sort(key=lambda record: record.station_id)

        logger.info(
            "afdc_ev_stations_received",
            state=normalized_state,
            records_received=len(records),
            total_results=total_results,
        )

        return records, total_results
