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
    b2_public_url_base: str | None = None
    gmi_api_key: str | None = None
    gmi_model: str | None = None
    generation_timeout_seconds: int = 300

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    def live_configuration_errors(self) -> list[str]:
        """Return missing live-mode settings without exposing credential values."""
        required = {
            "B2_KEY_ID": self.b2_key_id,
            "B2_APP_KEY": self.b2_app_key,
            "B2_BUCKET": self.b2_bucket,
            "B2_REGION": self.b2_region,
            "B2_PUBLIC_URL_BASE": self.b2_public_url_base,
            "GMI_API_KEY": self.gmi_api_key,
            "GMI_MODEL": self.gmi_model,
        }
        return [name for name, value in required.items() if not value]


@lru_cache
def get_settings() -> Settings:
    return Settings()
