from functools import lru_cache
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
    gmail_sync_enabled: bool = False
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
