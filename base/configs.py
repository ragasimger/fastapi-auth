import logging
import logging.config
from functools import lru_cache
from typing import Literal

from pydantic import computed_field, field_validator  # , PostgresDsn
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,  # DATABASE_URL == database_url
        extra="ignore",  # Don't explode on unknown env vars
    )

    # Application
    APP_NAME: str
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    ENVIRONMENT: Literal["development", "staging", "production"] = "development"

    # API
    API_V1_PREFIX: str = "/api/v1"
    API_V2_PREFIX: str = "/api/v2"

    SECRET_KEY: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    ALGORITHM: str = "HS256"

    # Database
    DB_DRIVER: str = "postgresql+asyncpg"
    DB_USER: str
    DB_PASSWORD: str
    DB_HOST: str
    DB_PORT: int = 5432
    DB_NAME: str
    # Connection pool - tune these for workload
    DB_POOL_SIZE: int = 20
    DB_MAX_OVERFLOW: int = 10
    DB_POOL_TIMEOUT: int = 30
    ATOMIC: bool = False

    @computed_field
    @property
    def DATABASE_URL(self) -> str:
        """
        Construct async database URL.

        Using asyncpg driver - THE correct choice for async PostgreSQL.
        psycopg2 is sync, psycopg3 works but asyncpg is battle-tested.
        """
        return (
            f"{self.DB_DRIVER}://{self.DB_USER}:{self.DB_PASSWORD}"
            f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
        )

    @computed_field
    @property
    def SYNC_DATABASE_URL(self) -> str:
        """For Alembic migrations - they run sync."""
        return (
            f"{self.DB_DRIVER}://{self.DB_USER}:{self.DB_PASSWORD}"
            f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
        )

    # CORS
    CORS_ORIGINS: list[str] = ["http://localhost:3000"]

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def parse_cors_origins(cls, v: str | list[str]) -> list[str]:
        """Handle comma-separated string from env var."""
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",")]
        return v

    # Rate limiting
    RATE_LIMIT_PER_MINUTE: int = 60


@lru_cache
def get_settings() -> Settings:
    """
    Cached settings instance.

    lru_cache ensures we don't re-parse env vars on every request.
    In tests, you can clear this cache to inject test settings.
    """
    return Settings()


@lru_cache
def get_swagger_settings() -> dict[str, str]:
    return {
        "persistAuthorization": True,
        "operationsSorter": "method",
        "tagsSorter": "alpha",
        "docExpansion": "none",
        "deepLinking": True,
        "displayRequestDuration": True,
        "showExtensions": True,
        "filter": True,  # built-in search bar
        "displayOperationId": True,
    }


def init_logging():
    from .logging_config import get_logging_configs

    logging.config.dictConfig(get_logging_configs())
    logger = logging.getLogger(__name__)

    logger.info(
        "\033[95m===============<-- Logging initialized -->===================\033[0m"
    )


settings = get_settings()

SWAGGER_UI_PARAMETERS = get_swagger_settings()
