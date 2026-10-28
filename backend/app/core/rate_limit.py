import logging
import time
from typing import Optional
from fastapi import HTTPException, Request, status
from backend.app.core.config import settings
from backend.app.core.redis_client import atomic_rate_limit, get_redis

logger = logging.getLogger("patriotaindica.ratelimit")

# Armazenamento em memória caso o Redis não esteja disponível (apenas para rotas não-críticas)
_in_memory_ratelimit: dict[str, list[float]] = {}


async def check_rate_limit(
    key: str,
    limit: int,
    window_seconds: int,
    error_msg: str = "Limite de requisições excedido. Tente novamente mais tarde.",
    fail_closed: bool = False,
) -> None:
    """
    Rate limiter por janela deslizante e contador atômico.
    - Utiliza o pool persistente do Redis via Lua Script atômico (INCR + EXPIRE).
    - Se fail_closed=True (rotas críticas: login, OTP, cadastro): rejeita com HTTP 503 se o Redis falhar.
    - Se fail_closed=False: faz fallback gracioso para memória local.
    """
    now = time.time()

    # 1. Tentar via pool persistente do Redis
    try:
        is_allowed, current_count = await atomic_rate_limit(key, limit, window_seconds)
        if not is_allowed:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=error_msg,
            )
        return
    except HTTPException:
        # Re-raise da exceção 429
        raise
    except Exception as exc:
        logger.warning("Falha ao consultar Redis para rate limit [key=%s]: %s", key, exc)
        if fail_closed and settings.ENVIRONMENT == "production":
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Serviço temporariamente indisponível para validação de segurança. Tente novamente em instantes.",
            )

    # 2. Fallback em memória (para rotas não-críticas quando Redis estiver indisponível)
    timestamps = _in_memory_ratelimit.get(key, [])
    cutoff = now - window_seconds
    timestamps = [ts for ts in timestamps if ts > cutoff]

    if len(timestamps) >= limit:
        _in_memory_ratelimit[key] = timestamps
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=error_msg,
        )

    timestamps.append(now)
    _in_memory_ratelimit[key] = timestamps


def get_client_ip(request: Request) -> str:
    """
    Obtém o IP real do cliente com validação rigorosa de borda (H1, T2.3):
    1. CF-Connecting-IP (Borda Cloudflare autêntica)
    2. X-Forwarded-For considerando TRUSTED_PROXY_HOPS (não aceita o primeiro item cego)
    3. X-Real-IP
    4. Client Host
    """
    # 1. Cloudflare header
    cf_ip = request.headers.get("CF-Connecting-IP")
    if cf_ip and cf_ip.strip():
        return cf_ip.strip()

    # 2. X-Forwarded-For protegido contra IP spoofing
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        ips = [ip.strip() for ip in forwarded.split(",") if ip.strip()]
        if ips:
            hops = settings.TRUSTED_PROXY_HOPS
            # O proxy confiável adiciona o IP do cliente antes dos seus próprios hops
            # Exemplo: client, proxy1, proxy2. Com hops=1, pegamos ips[-1]
            if len(ips) >= hops:
                return ips[-hops]
            return ips[0]

    # 3. X-Real-IP
    real_ip = request.headers.get("X-Real-IP")
    if real_ip and real_ip.strip():
        return real_ip.strip()

    # 4. Fallback padrão
    if request.client and request.client.host:
        return request.client.host

    return "127.0.0.1"
