from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

_ENV_FILE = Path(__file__).resolve().parent.parent.parent / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=_ENV_FILE, extra="ignore")

    environment: str = "development"
    database_url: str
    test_database_url: str | None = None

    secret_key: str
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 45
    refresh_token_expire_days: int = 30

    cors_origins: list[str] = ["http://localhost:3000"]

    rate_limit_enabled: bool = True
    rate_limit_requests: int = 100
    rate_limit_window_seconds: float = 60.0

    vapid_public_key: str | None = None
    vapid_private_key: str | None = None
    vapid_subject: str | None = None


settings = Settings()
