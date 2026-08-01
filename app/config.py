"""Application configuration."""

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Environment-backed settings with safe local defaults."""

    app_env: str = "development"
    app_base_url: str = "http://127.0.0.1:8000"
    data_dir: Path = Path("data")
    demo_mode: bool = True

    b2_key_id: str | None = None
    b2_app_key: str | None = None
    b2_bucket: str | None = None
    b2_region: str | None = None
    gmi_api_key: str | None = None

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()

