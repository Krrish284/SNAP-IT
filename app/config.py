"""Application configuration loaded from environment variables."""

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Typed application settings, populated from the environment and .env."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    database_url: str = Field(
        description="PostgreSQL connection string (Vercel Postgres or Neon, pooled)."
    )
    direct_url: str | None = Field(
        default=None,
        description="Direct (non-pooled) connection string used for schema bootstrap.",
    )
    base_url: str = Field(
        default="",
        description="Public base URL for short links (auto-detected from request when empty).",
    )
    short_code_length: int = Field(default=7, ge=4, le=12)
    cors_origins: str = Field(
        default="*",
        description="Comma-separated list of allowed CORS origins.",
    )
    debug: bool = False
    pool_min_size: int = Field(default=1, ge=0)
    pool_max_size: int = Field(default=10, ge=1)
    db_connect_timeout: float = Field(default=10.0, gt=0)
    db_retry_attempts: int = Field(default=3, ge=1, le=10)
    db_retry_backoff: float = Field(default=0.5, gt=0)
    max_referrer_length: int = Field(default=500, gt=0)
    dashboard_top_limit: int = Field(default=10, ge=1, le=100)
    create_link_attempts: int = Field(default=5, ge=1, le=20)


@lru_cache
def get_settings() -> Settings:
    """Return the cached application settings instance."""
    return Settings()
