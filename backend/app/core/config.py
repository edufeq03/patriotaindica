from typing import List, Optional
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import field_validator


class Settings(BaseSettings):
    PROJECT_NAME: str = "Patriota Indica"
    ENVIRONMENT: str = "production"
    DEBUG: bool = False

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

    # JWT Security - C1: Segredo obrigatório com validação rigorosa
    JWT_SECRET_KEY: str = "patriota_indica_sec_dev_key_64_chars_hex_948f2b7a1e0c45d3a9b8"
    JWT_ALGORITHM: str = "HS256"
    JWT_ISSUER: str = "patriotaindica.com.br"
    JWT_AUDIENCE: str = "patriotaindica-users"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # External APIs
    BRASILAPI_BASE_URL: str = "https://brasilapi.com.br/api"
    NOMINATIM_BASE_URL: str = "https://nominatim.openstreetmap.org"

    # Evolution WhatsApp API (Opcional - integração pronta)
    EVOLUTION_API_URL: Optional[str] = None
    EVOLUTION_API_KEY: Optional[str] = None
    EVOLUTION_INSTANCE_NAME: Optional[str] = None

    # CORS - M1: Restringir origens válidas sem curinga em produção
    CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "https://patriotaindica.com",
        "https://www.patriotaindica.com",
        "http://patriotaindica.com",
        "https://patriotaindica.com.br",
        "https://www.patriotaindica.com.br",
    ]

    # Host whitelist
    ALLOWED_HOSTS: List[str] = [
        "localhost",
        "127.0.0.1",
        "testserver",
        "backend",
        "backend:8000",
        "patriotaindica.com",
        "*.patriotaindica.com",
        "patriotaindica.com.br",
        "*.patriotaindica.com.br",
        "*",
    ]

    @field_validator("JWT_SECRET_KEY")
    @classmethod
    def strong_secret(cls, v: str) -> str:
        if len(v) < 32 or "change_this" in v.lower():
            raise ValueError(
                "JWT_SECRET_KEY fraco ou padrão detectado. Defina uma chave de pelo menos 32 caracteres gerada com openssl rand -hex 64."
            )
        return v

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="allow",
    )


settings = Settings()

