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
    if settings.DEBUG:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": str(exc)},
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

