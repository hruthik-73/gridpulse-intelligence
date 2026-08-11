from functools import lru_cache

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    eia_api_key: SecretStr = Field(alias="EIA_API_KEY")

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
