from fastapi import APIRouter
from backend.app.core.config import settings
from backend.app.api.v1.endpoints import (
    assisted,
    auth,
    businesses,
    categories,
    cities,
    claim,
    invitations,
    media,
    owner,
    privacy,
    redirects,
    search,
    triage,
    payments,
    whatsapp,
    owner_jobs,
    admin_jobs,
    public_jobs,
)

api_router = APIRouter()

# 1. Módulos do Núcleo Essencial (Sempre Ativos)
api_router.include_router(search.router, prefix="/search", tags=["Busca & Geolocalização"])
api_router.include_router(categories.router, prefix="/categories", tags=["Categorias"])
api_router.include_router(cities.router, prefix="/cities", tags=["Cidades & Expansão"])
api_router.include_router(businesses.router, prefix="/businesses", tags=["Empresas"])
api_router.include_router(redirects.router, prefix="/go", tags=["Rastreamento de Cliques"])
api_router.include_router(triage.router, prefix="/triage", tags=["Triagem & Curadoria"])
api_router.include_router(admin_jobs.router, prefix="/admin", tags=["Vagas & Moderação (Admin)"])
api_router.include_router(public_jobs.router, prefix="/jobs", tags=["Vagas de Emprego (Público)"])
api_router.include_router(auth.router, prefix="/auth", tags=["Autenticação"])
api_router.include_router(claim.router, prefix="/claim", tags=["Reivindicação & OTP"])
api_router.include_router(owner.router, prefix="/owner", tags=["Painel do Dono & Alterações"])
api_router.include_router(owner_jobs.router, prefix="/owner", tags=["Vagas de Emprego (Dono)"])
api_router.include_router(media.router, prefix="/media", tags=["Mídia & Upload"])
api_router.include_router(privacy.router, prefix="/privacy", tags=["Privacidade & LGPD"])

# 2. Monetização e Pagamentos (Controlado por FEATURE_PAYMENTS)
if settings.FEATURE_PAYMENTS:
    api_router.include_router(payments.router, prefix="/payments", tags=["Planos & Pagamentos"])

# 3. Módulos Congelados no MVP (Feature Flags)
if settings.FEATURE_ADMIN_TOOLS:
    api_router.include_router(invitations.router, prefix="/invitations", tags=["Convites Seguros"])
    api_router.include_router(assisted.router, prefix="/assisted", tags=["Cadastro Assistido & CSV"])

if settings.FEATURE_WHATSAPP_BOT:
    api_router.include_router(whatsapp.router, prefix="/webhooks/whatsapp", tags=["WhatsApp"])



