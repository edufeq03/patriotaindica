import logging
from typing import Optional, Tuple
import redis.asyncio as aioredis
from backend.app.core.config import settings

logger = logging.getLogger("patriotaindica.redis")

_redis_pool: Optional[aioredis.Redis] = None

# Lua script para rate limit atômico (INCR + EXPIRE garantidos sem race condition)
RATE_LIMIT_LUA = """
local current = redis.call('incr', KEYS[1])
if current == 1 then
    redis.call('expire', KEYS[1], tonumber(ARGV[1]))
end
return current
"""


async def init_redis_pool() -> Optional[aioredis.Redis]:
    """
    Inicializa o pool de conexões persistente do Redis no ciclo de vida (lifespan) da aplicação.
    """
    global _redis_pool
    try:
        _redis_pool = aioredis.from_url(
            settings.REDIS_URL,
            encoding="utf-8",
            decode_responses=True,
            max_connections=20,
            socket_timeout=2.0,
            socket_connect_timeout=2.0,
        )
        await _redis_pool.ping()
        logger.info("Pool de conexões Redis inicializado com sucesso.")
        return _redis_pool
    except Exception as exc:
        logger.warning("Não foi possível conectar ao Redis durante a inicialização: %s", exc)
        return None


async def close_redis_pool() -> None:
    """
    Fecha o pool de conexões no encerramento da aplicação.
    """
    global _redis_pool
    if _redis_pool is not None:
        try:
            await _redis_pool.aclose()
            logger.info("Pool de conexões Redis encerrado.")
        except Exception as exc:
            logger.warning("Erro ao encerrar pool de conexões Redis: %s", exc)
        finally:
            _redis_pool = None


def get_redis() -> Optional[aioredis.Redis]:
    """
    Retorna a instância do pool do Redis ou None se indisponível.
    """
    return _redis_pool


get_redis_client = get_redis



async def atomic_rate_limit(
    key: str, limit: int, window_seconds: int
) -> Tuple[bool, int]:
    """
    Executa rate limit atômico via Lua Script.
    Retorna (permitido: bool, contagem_atual: int).
    """
    client = get_redis()
    if client is None:
        raise ConnectionError("Redis não inicializado.")

    current = await client.eval(RATE_LIMIT_LUA, 1, key, str(window_seconds))
    current_count = int(current)
    is_allowed = current_count <= limit
    return is_allowed, current_count


async def store_refresh_token(jti: str, user_id: str, ttl_seconds: int) -> bool:
    """
    Armazena o refresh token ativo no Redis com TTL automático.
    Chave: rt:{jti} -> user_id
    """
    client = get_redis()
    if client is None:
        return False
    try:
        key = f"rt:{jti}"
        await client.set(key, str(user_id), ex=ttl_seconds)
        return True
    except Exception as exc:
        logger.error("Erro ao salvar refresh token no Redis: %s", exc)
        return False


async def verify_and_revoke_refresh_token(jti: str, user_id: str) -> bool:
    """
    Verifica se o refresh token é válido e o remove atomicamente (Rotação de Refresh Token).
    Se o jti não existir ou pertencer a outro usuário, falha e pode indicar reutilização maliciosa.
    """
    client = get_redis()
    if client is None:
        return False
    try:
        key = f"rt:{jti}"
        pipe = client.pipeline()
        pipe.get(key)
        pipe.delete(key)
        results = await pipe.execute()
        stored_user_id = results[0]
        if stored_user_id and str(stored_user_id) == str(user_id):
            return True
        return False
    except Exception as exc:
        logger.error("Erro ao validar e revogar refresh token no Redis: %s", exc)
        return False


async def revoke_refresh_token(jti: str) -> bool:
    """
    Revoga explicitamente um refresh token (Logout).
    """
    client = get_redis()
    if client is None:
        return False
    try:
        await client.delete(f"rt:{jti}")
        return True
    except Exception as exc:
        logger.error("Erro ao revogar refresh token no Redis: %s", exc)
        return False
