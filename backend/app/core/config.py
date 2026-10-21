from functools import lru_cache
from datetime import datetime, timezone
from pathlib import Path

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


BACKEND_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    db_host: str = "127.0.0.1"
    db_port: int = Field(default=5432, ge=1, le=65535)
    db_name: str = "jobtrack_db"
    db_user: str = "jobtrack_user"
    db_password: SecretStr
    google_oauth_client_id: str | None = None
    google_oauth_client_secret: str | None = None
    google_oauth_redirect_uri: str = (
        "http://localhost:8000/api/v1/auth/google/callback"
    )
    gmail_oauth_client_id: str | None = None
    gmail_oauth_client_secret: str | None = None
    gmail_oauth_redirect_uri: str = "http://localhost:8000/api/v1/gmail/callback"
    gmail_oauth_scope: str = "https://www.googleapis.com/auth/gmail.metadata"
    gmail_token_encryption_keys: str | None = None
    gmail_initial_sync_limit: int = Field(default=100, ge=1)
    gmail_backfill_after: datetime = datetime(2026, 10, 19, tzinfo=timezone.utc)
    gmail_sync_interval_seconds: int = Field(default=300, ge=30)
    gmail_sync_enabled: bool = False
    discovery_scheduler_enabled: bool = False
    discovery_refresh_interval_hours: int = Field(default=6, ge=1)
    discovery_lease_minutes: int = Field(default=15, ge=1)
    discovery_max_parallel: int = Field(default=2, ge=1, le=10)
    auth_frontend_url: str = "http://localhost:5173"
    auth_cookie_name: str = "jobtrack_session"
    auth_session_days: int = 7
    auth_oauth_transaction_minutes: int = 10
    auth_cookie_secure: bool = False
    auth_trusted_origins: list[str] = ["http://localhost:5173"]

    model_config = SettingsConfigDict(
        env_file=BACKEND_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
