from __future__ import annotations

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # ------------------------------------------------------------------
    # Application metadata
    # ------------------------------------------------------------------
    app_name: str = "Backend API"
    app_version: str = "0.1.0"

    # ------------------------------------------------------------------
    # Auth / JWT
    # ------------------------------------------------------------------
    secret_key: str
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30

    # ------------------------------------------------------------------
    # Database (Backend — MySQL / SQLite)
    # ------------------------------------------------------------------
    database_url: str
    create_tables_on_startup: bool = False

    # ------------------------------------------------------------------
    # Encryption
    # ------------------------------------------------------------------
    data_encryption_key: str | None = None

    # ------------------------------------------------------------------
    # Engine service
    # ------------------------------------------------------------------
    engine_api_url: str
    """Base HTTP URL of the Traffic Engine API, e.g. http://engine:8000"""

    engine_timeout: float = 10.0
    """Default timeout in seconds for HTTP requests to the Engine."""

    engine_retries: int = 2
    """Number of retry attempts for transient Engine failures."""

    # ------------------------------------------------------------------
    # CORS
    # ------------------------------------------------------------------
    cors_origins: list[str] = ["http://localhost:3000"]

    # ------------------------------------------------------------------
    # Logging
    # ------------------------------------------------------------------
    log_level: str = "INFO"
    log_file: str = "logs/app.txt"

    # ------------------------------------------------------------------
    # Pydantic-settings config
    # ------------------------------------------------------------------
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    # ------------------------------------------------------------------
    # Validators
    # ------------------------------------------------------------------

    @field_validator("engine_api_url")
    @classmethod
    def _strip_trailing_slash(cls, v: str) -> str:
        """Ensure the Engine URL never has a trailing slash."""
        return v.rstrip("/")

    @field_validator("log_level")
    @classmethod
    def _upper_log_level(cls, v: str) -> str:
        return v.upper()

    @property
    def engine_ws_url(self) -> str:
        """WebSocket base URL derived from engine_api_url."""
        return self.engine_api_url.replace("http://", "ws://").replace(
            "https://", "wss://"
        )


settings = Settings()
