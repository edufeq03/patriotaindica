from fastapi import APIRouter
from backend.app.api.v1.endpoints import (
    assisted,
    auth,
    businesses,
    categories,
    claim,
    invitations,
    media,
    owner,
    privacy,
    redirects,
    search,
    triage,
)

api_router = APIRouter()

api_router.include_router(search.router, prefix="/search", tags=["Busca & Geolocalização"])
api_router.include_router(categories.router, prefix="/categories", tags=["Categorias"])
api_router.include_router(businesses.router, prefix="/businesses", tags=["Empresas"])
api_router.include_router(redirects.router, prefix="/go", tags=["Rastreamento de Cliques"])
api_router.include_router(triage.router, prefix="/triage", tags=["Triagem & Curadoria"])
api_router.include_router(auth.router, prefix="/auth", tags=["Autenticação"])
api_router.include_router(claim.router, prefix="/claim", tags=["Reivindicação & OTP"])
api_router.include_router(owner.router, prefix="/owner", tags=["Painel do Dono & Alterações"])
api_router.include_router(invitations.router, prefix="/invitations", tags=["Convites Seguros"])
api_router.include_router(media.router, prefix="/media", tags=["Mídia & Upload"])
api_router.include_router(assisted.router, prefix="/assisted", tags=["Cadastro Assistido & CSV"])
api_router.include_router(privacy.router, prefix="/privacy", tags=["Privacidade & LGPD"])
