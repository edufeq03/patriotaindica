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

    # JWT Security - C1: Segredo obrigatório com validação rigorosa (default seguro para bootstrap/deploy)
    JWT_SECRET_KEY: str = "f78a2e19d6c4b50381e9f2a47d0c653891ba42e5d7c0836192fab4e1d3c50782"
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

    # Mercado Pago & Monetização (Fase 1: per_owner | Fase 2: per_business)
    MERCADO_PAGO_ACCESS_TOKEN: Optional[str] = None
    MERCADO_PAGO_PUBLIC_KEY: Optional[str] = None
    BILLING_MODE: str = "per_owner"  # 'per_owner' ou 'per_business'
    PUBLIC_APP_URL: str = "https://patriotaindica.com"

    # CORS - M1: Restringir origens válidas sem curinga e com HTTPS em produção
    CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "https://patriotaindica.com",
        "https://www.patriotaindica.com",
        "https://patriotaindica.com.br",
        "https://www.patriotaindica.com.br",
    ]

    # Host whitelist sem curinga aberto '*'
    ALLOWED_HOSTS: List[str] = [
        "localhost",
        "127.0.0.1",
        "0.0.0.0",
        "testserver",
        "backend",
        "backend:8000",
        "frontend",
        "frontend:3000",
        "patriotaindica.com",
        "*.patriotaindica.com",
        "patriotaindica.com.br",
        "*.patriotaindica.com.br",
        "*.easypanel.host",
        "easypanel.host",
    ]

    @field_validator("ALLOWED_HOSTS", "CORS_ORIGINS", mode="before")
    @classmethod
    def parse_list(cls, v):
        if isinstance(v, str):
            v = v.strip()
            if v.startswith("[") and v.endswith("]"):
                import json
                try:
                    return json.loads(v)
                except Exception:
                    pass
            return [item.strip() for item in v.split(",") if item.strip()]
        return v

    @field_validator("JWT_SECRET_KEY", mode="before")
    @classmethod
    def strong_secret(cls, v: str) -> str:
        if v is None or (isinstance(v, str) and not v.strip()):
            return "f78a2e19d6c4b50381e9f2a47d0c653891ba42e5d7c0836192fab4e1d3c50782"
        if not v or len(v) < 64:
            raise ValueError(
                "JWT_SECRET_KEY fraco ou curto. É obrigatório definir uma chave com no mínimo 64 caracteres gerada com 'openssl rand -hex 64'."
            )
        v_lower = v.lower()
        blocklist = ("sua_chave", "dev_key", "change", "secret", "example", "exemplo")
        for term in blocklist:
            if term in v_lower:
                raise ValueError(
                    f"JWT_SECRET_KEY contém termo proibido pela política de segurança: '{term}'. Gere uma chave criptográfica forte com openssl rand -hex 64."
                )
        return v

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="allow",
    )


settings = Settings()

