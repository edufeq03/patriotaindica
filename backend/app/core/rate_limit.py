import time
from typing import Optional
from fastapi import HTTPException, Request, status
from backend.app.core.config import settings

# Armazenamento em memória caso o Redis não esteja disponível
_in_memory_ratelimit: dict[str, list[float]] = {}


async def check_rate_limit(
    key: str,
    limit: int,
    window_seconds: int,
    error_msg: str = "Limite de requisições excedido. Tente novamente mais tarde.",
) -> None:
    """
    Rate limiter por janela deslizante.
    Tenta usar Redis; caso indisponível, usa fallback em memória com limpeza automática.
    """
    now = time.time()

    # Tentativa via Redis
    try:
        import redis.asyncio as aioredis
        redis_client = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
        try:
            n = await redis_client.incr(key)
            if n == 1:
                await redis_client.expire(key, window_seconds)
            if n > limit:
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail=error_msg,
                )
            return
        finally:
            await redis_client.aclose()
    except (ImportError, Exception) as e:
        # Se for o próprio HTTPException 429, re-raise!
        if isinstance(e, HTTPException):
            raise e
        # Se for erro de conexão do Redis, faz fallback gracioso para memória

    # Fallback em memória
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
    Obtém o IP real do cliente considerando headers de proxy confiável.
    """
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        # Pega o primeiro IP da cadeia (cliente original)
        return forwarded.split(",")[0].strip()
    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip.strip()
    if request.client and request.client.host:
        return request.client.host
    return "127.0.0.1"
