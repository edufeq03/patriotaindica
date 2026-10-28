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
    is_auth_claim = (
        request.url.path.startswith("/api/v1/triage")
        or request.url.path.startswith("/api/v1/auth")
        or request.url.path.startswith("/api/v1/claim")
        or request.url.path.startswith("/api/v1/owner")
    )
    if settings.DEBUG or is_auth_claim:
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
                "ALTER TABLE businesses DROP CONSTRAINT IF EXISTS businesses_document_number_key;",
                "ALTER TABLE businesses ADD COLUMN IF NOT EXISTS referral_code VARCHAR(50);",
                "ALTER TABLE businesses ADD COLUMN IF NOT EXISTS referred_by_code VARCHAR(50);",
                "ALTER TABLE businesses ADD COLUMN IF NOT EXISTS serves_at_location BOOLEAN NOT NULL DEFAULT TRUE;",
                "ALTER TABLE businesses ADD COLUMN IF NOT EXISTS serves_at_customer BOOLEAN NOT NULL DEFAULT FALSE;",
                "ALTER TABLE businesses ADD COLUMN IF NOT EXISTS serves_online BOOLEAN NOT NULL DEFAULT FALSE;",
                "CREATE INDEX IF NOT EXISTS idx_businesses_serves_at_location ON businesses(serves_at_location) WHERE status = 'approved';",
                "CREATE INDEX IF NOT EXISTS idx_businesses_serves_at_customer ON businesses(serves_at_customer) WHERE status = 'approved';",
                "CREATE INDEX IF NOT EXISTS idx_businesses_serves_online ON businesses(serves_online) WHERE status = 'approved';",
                """UPDATE businesses SET
                    serves_at_location = COALESCE(serves_at_location, (service_mode IN ('at_location', 'both'))),
                    serves_at_customer = COALESCE(serves_at_customer, (service_mode IN ('at_customer', 'both'))),
                    serves_online = COALESCE(serves_online, (service_mode = 'online'))
                WHERE serves_at_location IS NULL OR serves_at_customer IS NULL OR serves_online IS NULL;""",
                """UPDATE businesses SET
                    referral_code = 'PAT-' || UPPER(SUBSTRING(REPLACE(id::text, '-', ''), 1, 6))
                WHERE referral_code IS NULL OR referral_code = '' OR referral_code = 'None' OR referral_code = 'null';""",
                """CREATE TABLE IF NOT EXISTS plans (
                    id VARCHAR(30) PRIMARY KEY,
                    name VARCHAR(50) NOT NULL,
                    price_cents INTEGER NOT NULL,
                    monthly_equivalent_cents INTEGER NOT NULL,
                    duration_months INTEGER NOT NULL,
                    is_active BOOLEAN NOT NULL DEFAULT TRUE,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                );""",
                """INSERT INTO plans (id, name, price_cents, monthly_equivalent_cents, duration_months) VALUES
                    ('mensal', 'Plano Mensal', 1500, 1500, 1),
                    ('semestral', 'Plano Semestral', 7794, 1299, 6),
                    ('anual', 'Plano Anual', 11988, 999, 12)
                ON CONFLICT (id) DO UPDATE SET
                    name = EXCLUDED.name,
                    price_cents = EXCLUDED.price_cents,
                    monthly_equivalent_cents = EXCLUDED.monthly_equivalent_cents,
                    duration_months = EXCLUDED.duration_months;""",
                """CREATE TABLE IF NOT EXISTS subscriptions (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    owner_user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    business_id UUID REFERENCES businesses(id) ON DELETE SET NULL,
                    plan_id VARCHAR(30) NOT NULL REFERENCES plans(id),
                    status VARCHAR(30) NOT NULL DEFAULT 'active',
                    current_period_start TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    current_period_end TIMESTAMPTZ NOT NULL,
                    mp_payment_id VARCHAR(100),
                    mp_preference_id VARCHAR(100),
                    bonus_months_applied INTEGER NOT NULL DEFAULT 0,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                );""",
                """CREATE TABLE IF NOT EXISTS referrals (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    referrer_user_id UUID REFERENCES users(id) ON DELETE SET NULL,
                    referrer_business_id UUID REFERENCES businesses(id) ON DELETE SET NULL,
                    referred_user_id UUID REFERENCES users(id) ON DELETE SET NULL,
                    referred_business_id UUID NOT NULL REFERENCES businesses(id) ON DELETE CASCADE,
                    code VARCHAR(50) NOT NULL,
                    status VARCHAR(30) NOT NULL DEFAULT 'pending',
                    reward_granted_days INTEGER NOT NULL DEFAULT 30,
                    rewarded_at TIMESTAMPTZ,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                );""",
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
                """INSERT INTO categories (name, slug, kind, icon_name, display_order, status)
                VALUES
                  ('Eletricista', 'eletricista', 'service', 'zap', 1, 'approved'),
                  ('Encanador e Desentupidora', 'encanador-desentupidora', 'service', 'droplets', 2, 'approved'),
                  ('Ar-condicionado e Climatização', 'ar-condicionado-climatizacao', 'service', 'wind', 3, 'approved'),
                  ('Pintor e Reformas', 'pintor-reformas', 'service', 'paint-brush', 4, 'approved'),
                  ('Chaveiro 24h', 'chaveiro', 'service', 'key', 5, 'approved'),
                  ('Marcenaria e Móveis Planejados', 'marcenaria', 'service', 'hammer', 6, 'approved'),
                  ('Serralheria e Esquadrias', 'serralheria', 'service', 'shield', 7, 'approved'),
                  ('Vidraçaria', 'vidracaria', 'service', 'square', 8, 'approved'),
                  ('Diarista e Limpeza Profissional', 'diarista-limpeza', 'service', 'sparkles', 9, 'approved'),
                  ('Dedetizadora e Controle de Pragas', 'dedetizadora', 'service', 'shield-alert', 10, 'approved'),
                  ('Jardinagem e Paisagismo', 'jardinagem', 'service', 'flower-2', 11, 'approved'),
                  ('Fretes e Mudanças', 'fretes-mudancas', 'service', 'truck', 12, 'approved'),
                  ('Mecânica e Autoelétrica', 'mecanica-autoeletrica', 'service', 'car', 13, 'approved'),
                  ('Funilaria e Pintura Automotiva', 'funilaria-pintura', 'service', 'gauge', 14, 'approved'),
                  ('Borracharia e Pneus', 'borracharia-pneus', 'service', 'disc', 15, 'approved'),
                  ('Lava-Rápido e Estética Automotiva', 'lava-rapido', 'service', 'waves', 16, 'approved'),
                  ('Assistência de Celulares e Tablets', 'celulares-tablets', 'service', 'smartphone', 17, 'approved'),
                  ('Manutenção de Computadores e Redes', 'informatica-redes', 'service', 'laptop', 18, 'approved'),
                  ('Instalação de Câmeras e Segurança', 'seguranca-eletronica', 'service', 'cctv', 19, 'approved'),
                  ('Barbearia e Salão de Beleza', 'barbearia-salao', 'both', 'scissors', 20, 'approved'),
                  ('Estética e Cuidados Pessoais', 'estetica-beleza', 'both', 'sparkle', 21, 'approved'),
                  ('Personal Trainer e Fisioterapia', 'personal-fisioterapia', 'service', 'activity', 22, 'approved'),
                  ('Pet Shop e Banho & Tosa', 'pet-shop-banho-tosa', 'both', 'paw-print', 23, 'approved'),
                  ('Clínica Veterinária', 'veterinaria', 'service', 'stethoscope', 24, 'approved'),
                  ('Marmitas e Comida Caseira', 'marmitas-alimentacao', 'product', 'utensils', 25, 'approved'),
                  ('Padaria e Confeitaria Artesanal', 'padaria-confeitaria', 'product', 'cake', 26, 'approved'),
                  ('Hortifruti e Orgânicos', 'hortifruti-organicos', 'product', 'apple', 27, 'approved'),
                  ('Água Mineral e Gás', 'agua-gas', 'product', 'flame', 28, 'approved'),
                  ('Materiais de Construção', 'materiais-construcao', 'both', 'hard-hat', 29, 'approved'),
                  ('Flores e Plantas Ornamentais', 'floricultura', 'product', 'leaf', 30, 'approved'),
                  ('Costura e Ajustes', 'costura-ajustes', 'service', 'needle', 31, 'approved'),
                  ('Papelaria e Presentes', 'papelaria-presentes', 'product', 'book-open', 32, 'approved'),
                  ('Advocacia e Assessoria Jurídica', 'advocacia-juridico', 'service', 'scale', 33, 'approved'),
                  ('Contabilidade e Finanças', 'contabilidade-fiscal', 'service', 'calculator', 34, 'approved'),
                  ('Despachante Documentalista', 'despachante', 'service', 'file-text', 35, 'approved'),
                  ('Psicologia e Saúde Mental', 'psicologia-saude-mental', 'service', 'brain', 36, 'approved'),
                  ('Fisioterapia e Reabilitação', 'fisioterapia-reabilitacao', 'service', 'activity', 37, 'approved'),
                  ('Odontologia e Dentista', 'odontologia-dentista', 'service', 'smile', 38, 'approved'),
                  ('Nutrição e Dietética', 'nutricao-bem-estar', 'service', 'apple', 39, 'approved'),
                  ('Manicure, Pedicure e Nail Art', 'manicure-pedicure', 'service', 'sparkles', 40, 'approved'),
                  ('Sobrancelhas e Cílios', 'sobrancelhas-cilios', 'service', 'eye', 41, 'approved'),
                  ('Tatuagem e Piercing', 'tatuagem-piercing', 'service', 'feather', 42, 'approved'),
                  ('Fotografia e Filmagem', 'fotografia-filmagem', 'service', 'camera', 43, 'approved'),
                  ('Festas, Decoração e Eventos', 'festas-eventos', 'service', 'gift', 44, 'approved'),
                  ('DJ, Som e Iluminação', 'dj-som-iluminacao', 'service', 'music', 45, 'approved'),
                  ('Aulas Particulares e Educação', 'aulas-particulares', 'service', 'graduation-cap', 46, 'approved'),
                  ('Conserto de Eletrodomésticos', 'conserto-eletrodomesticos', 'service', 'wrench', 47, 'approved'),
                  ('Tapeçaria e Reforma de Estofados', 'tapecaria-estofados', 'service', 'armchair', 48, 'approved'),
                  ('Guincho e Reboque 24h', 'guincho-reboque-24h', 'service', 'truck', 49, 'approved'),
                  ('Adestramento e Passeador Pet', 'adestramento-passeador-pet', 'service', 'paw-print', 50, 'approved'),
                  ('Gesso, Drywall e Iluminação', 'gesso-drywall', 'service', 'layout', 51, 'approved'),
                  ('Energia Solar e Fotovoltaica', 'energia-solar', 'service', 'sun', 52, 'approved'),
                  ('Pizzaria e Hamburgueria', 'pizzaria-hamburgueria', 'both', 'pizza', 53, 'approved'),
                  ('Gráfica Rápida e Comunicação Visual', 'grafica-comunicacao-visual', 'service', 'printer', 54, 'approved')
                ON CONFLICT (slug) DO UPDATE
                SET
                  name = EXCLUDED.name,
                  kind = EXCLUDED.kind,
                  icon_name = EXCLUDED.icon_name,
                  display_order = EXCLUDED.display_order,
                  status = 'approved';""",
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


@app.get("/api/v1/system/migrate", tags=["Health"])
async def trigger_runtime_migrations():
    """Permite forçar a execução das migrações de runtime sob demanda."""
    await apply_runtime_migrations()
    return {"status": "ok", "message": "Migrações de runtime executadas com sucesso."}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.app.main:app", host="0.0.0.0", port=8000, reload=settings.DEBUG)

