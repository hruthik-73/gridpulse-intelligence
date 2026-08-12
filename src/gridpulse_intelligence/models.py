"""Typed data models used by GridPulse Intelligence."""

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class GridRegionRecord(BaseModel):
    """Validated hourly regional electricity record from EIA."""

    model_config = ConfigDict(
        populate_by_name=True,
        extra="forbid",
    )

    period: datetime
    respondent: str
    respondent_name: str = Field(alias="respondent-name")
    record_type: str = Field(alias="type")
    type_name: str = Field(alias="type-name")
    value: float
    value_units: str = Field(alias="value-units")

    @field_validator("period", mode="before")
    @classmethod
    def parse_period(cls, value: object) -> datetime:
        if isinstance(value, datetime):
            return value

        if not isinstance(value, str):
            raise ValueError("period must be a string or datetime")

        supported_formats = (
            "%Y-%m-%dT%H",
            "%Y-%m-%dT%H:%M:%S",
        )

        for date_format in supported_formats:
            try:
                return datetime.strptime(
                    value,
                    date_format,
                )
            except ValueError:
                continue

        raise ValueError("period must use YYYY-MM-DDTHH or YYYY-MM-DDTHH:MM:SS")

    @field_validator(
        "respondent",
        "respondent_name",
        "record_type",
        "type_name",
    )
    @classmethod
    def validate_non_empty_text(
        cls,
        value: str,
    ) -> str:
        cleaned = value.strip()

        if not cleaned:
            raise ValueError("value must not be empty")

        return cleaned

    @field_validator("value_units")
    @classmethod
    def normalize_units(
        cls,
        value: str,
    ) -> str:
        return value.strip().lower()


class WeatherForecastRecord(BaseModel):
    """Normalized hourly weather forecast from NWS."""

    model_config = ConfigDict(
        extra="forbid",
    )

    latitude: float
    longitude: float
    period_start: datetime
    period_end: datetime
    temperature: float
    temperature_unit: str
    precipitation_probability: float | None = None
    relative_humidity: float | None = None
    wind_speed: str
    wind_direction: str
    short_forecast: str

    @field_validator(
        "period_start",
        "period_end",
    )
    @classmethod
    def require_timezone(
        cls,
        value: datetime,
    ) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("weather timestamps must be timezone-aware")

        return value

    @field_validator(
        "temperature_unit",
        "wind_speed",
        "wind_direction",
        "short_forecast",
    )
    @classmethod
    def validate_weather_text(
        cls,
        value: str,
    ) -> str:
        cleaned = value.strip()

        if not cleaned:
            raise ValueError("weather text fields must not be empty")

        return cleaned


class EVChargingStationRecord(BaseModel):
    """Normalized public EV charging station from AFDC."""

    model_config = ConfigDict(
        extra="forbid",
    )

    station_id: int
    station_name: str

    street_address: str | None = None
    city: str
    state: str
    zip_code: str
    country: str

    latitude: float = Field(
        ge=-90,
        le=90,
    )

    longitude: float = Field(
        ge=-180,
        le=180,
    )

    fuel_type_code: Literal["ELEC"]
    access_code: Literal["public"]
    status_code: Literal["E"]

    ev_network: str | None = None
    ev_connector_types: list[str] = Field(default_factory=list)

    ev_level1_evse_num: int | None = None
    ev_level2_evse_num: int | None = None
    ev_dc_fast_num: int | None = None

    facility_type: str | None = None

    date_last_confirmed: date | None = None
    updated_at: datetime | None = None

    @field_validator(
        "station_name",
        "city",
        "state",
        "zip_code",
        "country",
    )
    @classmethod
    def validate_station_text(
        cls,
        value: str,
    ) -> str:
        cleaned = value.strip()

        if not cleaned:
            raise ValueError("station text fields must not be empty")

        return cleaned

    @field_validator("state")
    @classmethod
    def normalize_state(
        cls,
        value: str,
    ) -> str:
        return value.upper()

    @field_validator("country")
    @classmethod
    def normalize_country(
        cls,
        value: str,
    ) -> str:
        return value.upper()

    @field_validator(
        "ev_level1_evse_num",
        "ev_level2_evse_num",
        "ev_dc_fast_num",
    )
    @classmethod
    def validate_evse_count(
        cls,
        value: int | None,
    ) -> int | None:
        if value is not None and value < 0:
            raise ValueError("EVSE counts cannot be negative")

        return value
