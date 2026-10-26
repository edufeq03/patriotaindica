from fastapi import APIRouter
from backend.app.api.v1.endpoints import (
    auth,
    businesses,
    categories,
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
