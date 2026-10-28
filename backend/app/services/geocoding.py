import json
import logging
from typing import Optional, Tuple
import httpx
from backend.app.core.redis_client import get_redis

logger = logging.getLogger(__name__)

# Fallback em memória para ambientes sem Redis ou testes unitários
_geocoding_cache: dict[str, Tuple[Optional[float], Optional[float], str, float]] = {}


async def geocode_address(
    postal_code: Optional[str] = None,
    city: Optional[str] = None,
    state: Optional[str] = None,
    street: Optional[str] = None,
    number: Optional[str] = None,
) -> Tuple[Optional[float], Optional[float], str, float]:
    """
    Geocodificação server-side nacional (T3.2).
    Retorna: (latitude, longitude, source, confidence)
    
    Fontes:
    1. Cache persistente no Redis (TTL: 30 dias) / Fallback memória
    2. BrasilAPI CEP v2 (inclui coordenadas IBGE/Mapas quando disponíveis)
    3. OpenStreetMap / Nominatim (respeitando User-Agent oficial e rate limit)
    
    SEGURANÇA (H4, T3.2):
    NUNCA aplicar fallback cego para Campinas. Se a geocodificação falhar,
    retorna (None, None, 'unresolved', 0.0) para que a candidatura
    receba location_pending = True e seja ajustada na triagem manual.
    """
    clean_cep = "".join(filter(str.isdigit, postal_code or ""))
    cache_key = f"geo:{clean_cep}:{city or ''}:{state or ''}".lower()

    # 1. Checar cache do Redis
    redis = get_redis()
    if redis:
        try:
            cached_val = await redis.get(cache_key)
            if cached_val:
                lat, lng, src, conf = json.loads(cached_val)
                return lat, lng, src, conf
        except Exception as exc:
            logger.warning("Falha ao ler cache de geocodificacao do Redis: %s", exc)

    # 2. Checar cache em memória
    if cache_key in _geocoding_cache:
        return _geocoding_cache[cache_key]

    async with httpx.AsyncClient(timeout=8.0) as client:
        # 3. Tentar BrasilAPI CEP v2
        if len(clean_cep) == 8:
            try:
                resp = await client.get(f"https://brasilapi.com.br/api/cep/v2/{clean_cep}")
                if resp.status_code == 200:
                    data = resp.json()
                    location = data.get("location", {})
                    coordinates = location.get("coordinates", {})
                    lng = coordinates.get("longitude")
                    lat = coordinates.get("latitude")

                    if lat and lng:
                        try:
                            lat_f = float(lat)
                            lng_f = float(lng)
                            if -90.0 <= lat_f <= 90.0 and -180.0 <= lng_f <= 180.0:
                                res = (lat_f, lng_f, "brasilapi", 0.9)
                                await _save_cache(cache_key, res)
                                return res
                        except (ValueError, TypeError):
                            pass
            except Exception as e:
                logger.warning("Erro ao consultar BrasilAPI para CEP %s: %s", clean_cep, e)

        # 4. Fallback Nominatim (OpenStreetMap)
        try:
            query_parts = []
            if clean_cep:
                query_parts.append(clean_cep)
            if city:
                query_parts.append(city)
            if state:
                query_parts.append(state)
            query_parts.append("Brasil")

            q = ", ".join(query_parts)
            headers = {"User-Agent": "PatriotaIndicaGeocoding/2.0 (contato@patriotaindica.com.br)"}
            resp = await client.get(
                "https://nominatim.openstreetmap.org/search",
                params={"q": q, "format": "json", "limit": 1, "countrycodes": "br"},
                headers=headers,
            )
            if resp.status_code == 200:
                results = resp.json()
                if results and len(results) > 0:
                    lat_f = float(results[0]["lat"])
                    lng_f = float(results[0]["lon"])
                    res = (lat_f, lng_f, "nominatim", 0.75)
                    await _save_cache(cache_key, res)
                    return res
        except Exception as e:
            logger.warning("Erro ao consultar Nominatim para %s: %s", cache_key, e)

    # 5. Não resolvido: vai para triagem manual sem inventar coordenadas
    unresolved_res = (None, None, "unresolved", 0.0)
    await _save_cache(cache_key, unresolved_res, ttl=3600)  # Cache curto para não ficar chamando API repetidamente
    return unresolved_res


async def _save_cache(
    cache_key: str,
    data: Tuple[Optional[float], Optional[float], str, float],
    ttl: int = 30 * 86400,
) -> None:
    _geocoding_cache[cache_key] = data
    redis = get_redis()
    if redis:
        try:
            await redis.set(cache_key, json.dumps(data), ex=ttl)
        except Exception as exc:
            logger.warning("Falha ao salvar geocodificacao no Redis: %s", exc)
