"""Application configuration for GridPulse Intelligence."""

from functools import lru_cache

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Environment-backed application settings."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    eia_api_key: SecretStr = Field(
        alias="EIA_API_KEY",
    )

    afdc_api_key: SecretStr | None = Field(
        default=None,
        alias="AFDC_API_KEY",
    )

    noaa_user_agent: str = Field(
        default="GridPulseIntelligence/0.1",
        alias="NOAA_USER_AGENT",
    )

    app_env: str = Field(
        default="development",
        alias="APP_ENV",
    )

    log_level: str = Field(
        default="INFO",
        alias="LOG_LEVEL",
    )


@lru_cache
def get_settings() -> Settings:
    """Return cached application settings."""

    return Settings()
