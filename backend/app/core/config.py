from typing import List, Union
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import AnyHttpUrl, validator


class Settings(BaseSettings):
    PROJECT_NAME: str = "Patriota Indica"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True

    # Database
    POSTGRES_SERVER: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "postgres"
    POSTGRES_DB: str = "patriotaindica"
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/patriotaindica"
    DATABASE_SYNC_URL: str = "postgresql://postgres:postgres@localhost:5432/patriotaindica"

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # JWT Security
    JWT_SECRET_KEY: str = "change_this_to_a_very_secure_random_string_in_production_32_chars"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440

    # External APIs
    BRASILAPI_BASE_URL: str = "https://brasilapi.com.br/api"
    NOMINATIM_BASE_URL: str = "https://nominatim.openstreetmap.org"

    # CORS
    CORS_ORIGINS: List[str] = ["http://localhost:3000", "http://127.0.0.1:3000"]

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="allow",
    )


settings = Settings()
