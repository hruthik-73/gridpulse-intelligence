"""Client for the National Weather Service API."""

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
from gridpulse_intelligence.models import WeatherForecastRecord

logger = structlog.get_logger(__name__)

Record = dict[str, object]


class NWSError(Exception):
    """Base exception for NWS API failures."""


class NWSTransientError(NWSError):
    """Temporary NWS API failure that may succeed after retrying."""


class NWSClient:
    """Client for retrieving normalized NWS weather forecasts."""

    BASE_URL: Final[str] = "https://api.weather.gov"

    def __init__(
        self,
        timeout_seconds: float = 20.0,
    ) -> None:
        settings = get_settings()

        self._client = httpx.Client(
            base_url=self.BASE_URL,
            timeout=httpx.Timeout(timeout_seconds),
            headers={
                "Accept": "application/geo+json",
                "User-Agent": settings.noaa_user_agent,
            },
        )

    def close(self) -> None:
        """Close the underlying HTTP client."""

        self._client.close()

    @retry(
        retry=retry_if_exception_type(NWSTransientError),
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
    ) -> Record:
        """Request JSON from the NWS API."""

        logger.info(
            "nws_request_started",
            endpoint=endpoint,
        )

        try:
            response = self._client.get(endpoint)
        except httpx.RequestError:
            logger.warning(
                "nws_network_error",
                endpoint=endpoint,
            )
            raise NWSTransientError("Network error while contacting the NWS API.") from None

        if response.status_code == 429 or response.status_code >= 500:
            logger.warning(
                "nws_transient_error",
                endpoint=endpoint,
                status_code=response.status_code,
            )

            raise NWSTransientError(
                f"NWS API temporarily unavailable. Status: {response.status_code}"
            )

        if response.status_code >= 400:
            raise NWSError(f"NWS API request failed. Status: {response.status_code}")

        try:
            payload: object = response.json()
        except ValueError:
            raise NWSError("NWS API returned invalid JSON.") from None

        if not isinstance(payload, dict):
            raise NWSError("Unexpected NWS API response format.")

        logger.info(
            "nws_request_completed",
            endpoint=endpoint,
            status_code=response.status_code,
        )

        return {str(key): value for key, value in payload.items()}

    @staticmethod
    def _mapping(
        value: object,
        name: str,
    ) -> Record:
        """Require a mapping value."""

        if not isinstance(value, dict):
            raise NWSError(f"NWS response is missing {name}.")

        return {str(key): item for key, item in value.items()}

    @staticmethod
    def _text(
        record: Record,
        key: str,
    ) -> str:
        """Extract a required string field."""

        value = record.get(key)

        if not isinstance(value, str) or not value.strip():
            raise NWSError(f"NWS response contains invalid {key}.")

        return value

    @staticmethod
    def _number(
        record: Record,
        key: str,
    ) -> float:
        """Extract a required numeric field."""

        value = record.get(key)

        if not isinstance(value, (int, float)) or isinstance(value, bool):
            raise NWSError(f"NWS response contains invalid {key}.")

        return float(value)

    @classmethod
    def _quantity_value(
        cls,
        record: Record,
        key: str,
    ) -> float | None:
        """Extract the value from an NWS quantitative value."""

        raw_quantity = record.get(key)

        if raw_quantity is None:
            return None

        quantity = cls._mapping(
            raw_quantity,
            key,
        )

        raw_value = quantity.get("value")

        if raw_value is None:
            return None

        if not isinstance(raw_value, (int, float)) or isinstance(raw_value, bool):
            raise NWSError(f"NWS response contains invalid {key} value.")

        return float(raw_value)

    def get_hourly_forecast(
        self,
        latitude: float,
        longitude: float,
        limit: int = 24,
    ) -> list[WeatherForecastRecord]:
        """Return normalized hourly forecast periods for a point."""

        if not -90 <= latitude <= 90:
            raise ValueError("latitude must be between -90 and 90")

        if not -180 <= longitude <= 180:
            raise ValueError("longitude must be between -180 and 180")

        if limit < 1:
            raise ValueError("limit must be greater than zero")

        point_payload = self._request(f"/points/{latitude:.4f},{longitude:.4f}")

        point_properties = self._mapping(
            point_payload.get("properties"),
            "point properties",
        )

        forecast_hourly = self._text(
            point_properties,
            "forecastHourly",
        )

        forecast_payload = self._request(
            forecast_hourly,
        )

        forecast_properties = self._mapping(
            forecast_payload.get("properties"),
            "forecast properties",
        )

        raw_periods = forecast_properties.get("periods")

        if not isinstance(raw_periods, list):
            raise NWSError("NWS response is missing forecast periods.")

        records: list[WeatherForecastRecord] = []

        for raw_period in raw_periods[:limit]:
            period = self._mapping(
                raw_period,
                "forecast period",
            )

            record = WeatherForecastRecord(
                latitude=latitude,
                longitude=longitude,
                period_start=self._text(
                    period,
                    "startTime",
                ),
                period_end=self._text(
                    period,
                    "endTime",
                ),
                temperature=self._number(
                    period,
                    "temperature",
                ),
                temperature_unit=self._text(
                    period,
                    "temperatureUnit",
                ),
                precipitation_probability=(
                    self._quantity_value(
                        period,
                        "probabilityOfPrecipitation",
                    )
                ),
                relative_humidity=(
                    self._quantity_value(
                        period,
                        "relativeHumidity",
                    )
                ),
                wind_speed=self._text(
                    period,
                    "windSpeed",
                ),
                wind_direction=self._text(
                    period,
                    "windDirection",
                ),
                short_forecast=self._text(
                    period,
                    "shortForecast",
                ),
            )

            records.append(record)

        logger.info(
            "nws_hourly_forecast_received",
            latitude=latitude,
            longitude=longitude,
            record_count=len(records),
        )

        return records
