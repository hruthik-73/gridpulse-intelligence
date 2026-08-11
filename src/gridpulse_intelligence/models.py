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

    respondent_name: str = Field(
        alias="respondent-name",
    )

    record_type: str = Field(
        alias="type",
    )

    type_name: str = Field(
        alias="type-name",
    )

    value: float

    value_units: str = Field(
        alias="value-units",
    )

    @field_validator("period", mode="before")
    @classmethod
    def parse_period(cls, value: object) -> datetime:
        """Convert EIA and stored ISO period values into datetime objects."""

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
    def validate_non_empty_text(cls, value: str) -> str:
        """Reject unexpectedly empty identifying fields."""

        cleaned = value.strip()

        if not cleaned:
            raise ValueError("value must not be empty")

        return cleaned

    @field_validator("value_units")
    @classmethod
    def normalize_units(cls, value: str) -> str:
        """Normalize units for downstream processing."""

        return value.strip().lower()
