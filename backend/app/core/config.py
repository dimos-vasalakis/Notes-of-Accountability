from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    environment: str = "development"
    database_url: str
    test_database_url: str | None = None

    secret_key: str
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 45
    refresh_token_expire_days: int = 30

    cors_origins: list[str] = ["http://localhost:3000"]


settings = Settings()
