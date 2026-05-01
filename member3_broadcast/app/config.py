from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "Member 3 Real-Time Broadcast Service"
    jwt_secret: str = "change-me-change-me-change-me-12345"
    jwt_algorithm: str = "HS256"
    forecast_upstream_url: str = "http://member1:8000"
    redis_url: str = "redis://localhost:6379/0"
    kafka_bootstrap_servers: str = "localhost:9092"
    postgres_dsn: str = "postgresql+asyncpg://user:pass@localhost:5432/campus"


@lru_cache
def get_settings() -> Settings:
    return Settings()
