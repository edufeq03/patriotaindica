import logging
from typing import Optional, Tuple
import httpx

logger = logging.getLogger(__name__)

# Cache simples em memória para evitar chamadas redundantes
_geocoding_cache: dict[str, Tuple[float, float, str, float]] = {}


async def geocode_address(
    postal_code: Optional[str] = None,
    city: Optional[str] = None,
    state: Optional[str] = None,
    street: Optional[str] = None,
    number: Optional[str] = None,
) -> Tuple[Optional[float], Optional[float], str, float]:
    """
    Geocodificação server-side nacional.
    Retorna: (latitude, longitude, source, confidence)
    
    Fontes:
    1. BrasilAPI CEP v2 (inclui coordenadas IBGE/Mapas quando disponíveis)
    2. OpenStreetMap / Nominatim (fallback com busca por CEP ou Cidade + UF)
    
    SEGURANÇA (H4):
    NUNCA aplicar fallback cego para Campinas. Se a geocodificação falhar,
    retorna (None, None, 'unresolved', 0.0) para que a candidatura
    seja resolvida na triagem manual.
    """
    clean_cep = "".join(filter(str.isdigit, postal_code or ""))
    cache_key = f"{clean_cep}:{city}:{state}"

    if cache_key in _geocoding_cache:
        return _geocoding_cache[cache_key]

    async with httpx.AsyncClient(timeout=8.0) as client:
        # 1. Tentar BrasilAPI CEP v2
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
                                _geocoding_cache[cache_key] = res
                                return res
                        except (ValueError, TypeError):
                            pass
            except Exception as e:
                logger.warning(f"Erro ao consultar BrasilAPI para CEP {clean_cep}: {e}")

        # 2. Fallback Nominatim (OpenStreetMap)
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
            headers = {"User-Agent": "PatriotaIndicaGeocoding/1.0 (contato@patriotaindica.com.br)"}
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
                    _geocoding_cache[cache_key] = res
                    return res
        except Exception as e:
            logger.warning(f"Erro ao consultar Nominatim para {cache_key}: {e}")

    # Não resolvido: vai para triagem manual sem inventar coordenadas
    return (None, None, "unresolved", 0.0)
