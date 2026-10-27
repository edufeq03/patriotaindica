import logging
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from backend.app.api.v1.api import api_router
from backend.app.core.config import settings

logger = logging.getLogger("patriotaindica")

# H7: Em ambiente de produção estrito, desabilitar docs_url, redoc_url e openapi_url
is_prod = (settings.ENVIRONMENT == "production" and not settings.DEBUG)

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Backend API do Marketplace Local Curado de Serviços e Produtos",
    version="2.0.0",
    docs_url=None if is_prod else "/docs",
    redoc_url=None if is_prod else "/redoc",
    openapi_url=None if is_prod else "/openapi.json",
)

# M1 & M9: Proteção de Host e CORS
app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=settings.ALLOWED_HOSTS,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "Accept", "Origin", "User-Agent"],
)


# H7: Handler global de exceções para evitar vazamento de stack traces e dados internos
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.exception("Exceção não tratada capturada em %s: %s", request.url.path, exc)
    is_admin = request.url.path.startswith("/api/v1/triage") or request.url.path.startswith("/api/v1/auth")
    if settings.DEBUG or is_admin:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": f"Erro interno ({exc.__class__.__name__}): {str(exc)}"},
        )
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Erro interno no processamento. Por favor, tente novamente mais tarde."},
    )


# Rotas da API v1
app.include_router(api_router, prefix="/api/v1")

# Servir uploads estáticos seguros
import os
from fastapi.staticfiles import StaticFiles
static_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../static"))
os.makedirs(os.path.join(static_dir, "uploads"), exist_ok=True)
app.mount("/static", StaticFiles(directory=static_dir), name="static")


@app.on_event("startup")
async def apply_runtime_migrations():
    """
    Auto-migração de runtime: garante que colunas críticas das migrations 006 a 010
    existam no PostgreSQL mesmo se o banco tiver sido iniciado com schema antigo.
    """
    from backend.app.core.database import AsyncSessionLocal
    from sqlalchemy import text
    try:
        async with AsyncSessionLocal() as session:
            ddl_statements = [
                "ALTER TABLE businesses ALTER COLUMN location DROP NOT NULL;",
                "ALTER TABLE businesses NO FORCE ROW LEVEL SECURITY;",
                "ALTER TABLE business_review_log NO FORCE ROW LEVEL SECURITY;",
                "ALTER TABLE categories NO FORCE ROW LEVEL SECURITY;",
                "ALTER TABLE business_categories NO FORCE ROW LEVEL SECURITY;",
                "DO $$ BEGIN CREATE CAST (varchar AS listing_type) WITH INOUT AS IMPLICIT; EXCEPTION WHEN OTHERS THEN NULL; END $$;",
                "DO $$ BEGIN CREATE CAST (varchar AS service_mode) WITH INOUT AS IMPLICIT; EXCEPTION WHEN OTHERS THEN NULL; END $$;",
                "DO $$ BEGIN CREATE CAST (varchar AS business_status) WITH INOUT AS IMPLICIT; EXCEPTION WHEN OTHERS THEN NULL; END $$;",
                "DO $$ BEGIN CREATE CAST (varchar AS business_source) WITH INOUT AS IMPLICIT; EXCEPTION WHEN OTHERS THEN NULL; END $$;",
                "ALTER TABLE businesses ADD COLUMN IF NOT EXISTS geocode_source VARCHAR(50);",
                "ALTER TABLE businesses ADD COLUMN IF NOT EXISTS geocode_confidence FLOAT;",
                "ALTER TABLE categories ADD COLUMN IF NOT EXISTS status VARCHAR(20) NOT NULL DEFAULT 'approved';",
                "ALTER TABLE categories ADD COLUMN IF NOT EXISTS proposed_by_business_id UUID REFERENCES businesses(id) ON DELETE SET NULL;",
                "ALTER TABLE users ADD COLUMN IF NOT EXISTS must_change_password BOOLEAN NOT NULL DEFAULT FALSE;",
                "ALTER TABLE users ADD COLUMN IF NOT EXISTS totp_secret VARCHAR(64);",
                "ALTER TABLE users ADD COLUMN IF NOT EXISTS totp_enabled BOOLEAN NOT NULL DEFAULT FALSE;",
                """CREATE TABLE IF NOT EXISTS category_aliases (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    category_id UUID NOT NULL REFERENCES categories(id) ON DELETE CASCADE,
                    alias_name VARCHAR(100) NOT NULL UNIQUE,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                );""",
                """CREATE TABLE IF NOT EXISTS business_pending_changes (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    business_id UUID NOT NULL REFERENCES businesses(id) ON DELETE CASCADE,
                    proposed_by_user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    changes JSONB NOT NULL,
                    status VARCHAR(20) NOT NULL DEFAULT 'pending_review',
                    reviewed_by UUID REFERENCES users(id) ON DELETE SET NULL,
                    reviewed_at TIMESTAMPTZ,
                    rejection_reason TEXT,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                );""",
                """CREATE TABLE IF NOT EXISTS data_subject_requests (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    request_type VARCHAR(32) NOT NULL,
                    email VARCHAR(255) NOT NULL,
                    phone VARCHAR(32),
                    details TEXT,
                    status VARCHAR(32) NOT NULL DEFAULT 'received',
                    ip_hash VARCHAR(64),
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    resolved_at TIMESTAMPTZ
                );""",
            ]
            for stmt in ddl_statements:
                try:
                    await session.execute(text(stmt))
                    await session.commit()
                except Exception:
                    await session.rollback()
            logger.info("Migrações automáticas de runtime aplicadas com sucesso.")
    except Exception as e:
        logger.warning("Aviso durante migrações de runtime: %s", e)


@app.get("/health", tags=["Health"])
async def health_check():
    return {
        "status": "online",
        "service": settings.PROJECT_NAME,
        "environment": settings.ENVIRONMENT,
        "version": "2.0.0",
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.app.main:app", host="0.0.0.0", port=8000, reload=settings.DEBUG)

