"""Typed data models used by GridPulse Intelligence."""

from datetime import datetime

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
