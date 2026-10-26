from typing import Any, Dict, List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.database import get_db
from backend.app.core.rate_limit import check_rate_limit, get_client_ip

router = APIRouter()


@router.get("", response_model=Dict[str, Any])
async def search_nearby_businesses(
    request: Request,
    lat: Optional[float] = Query(None, ge=-90.0, le=90.0, description="Latitude do usuário (opcional para busca nacional)"),
    lng: Optional[float] = Query(None, ge=-180.0, le=180.0, description="Longitude do usuário (opcional para busca nacional)"),
    radius_km: float = Query(50.0, ge=1.0, le=100.0, description="Raio de busca em km (máximo 100 km)"),
    q: Optional[str] = Query(None, max_length=80, description="Busca textual (máx 80 caracteres)"),
    category_id: Optional[UUID] = Query(None, description="Filtro por categoria"),
    listing_type: Optional[str] = Query(None, description="'service', 'product', ou 'both'"),
    state: Optional[str] = Query(None, max_length=2, description="Filtro por Estado/UF (ex: SP, PR, SC)"),
    city: Optional[str] = Query(None, max_length=100, description="Filtro por Cidade"),
    page: int = Query(1, ge=1, le=50, description="Página (teto de 50 páginas)"),
    limit: int = Query(20, ge=1, le=50, description="Itens por página (máx 50)"),
    db: AsyncSession = Depends(get_db),
):
    """
    Busca nacional e por proximidade geográfica:
    SEGURANÇA:
    - [H1] Rate limit por IP (60/min).
    - [H6] Ocultação de WhatsApp e telefone nos cards para impedir raspagem em massa (scraping).
    - [M4] Tetos rígidos de consulta (q <= 80, radius <= 100, page <= 50, CAST seguro de tipo).
    - [Nacional] Suporte a busca em todo o Brasil ou filtrada por UF e Cidade.
    """
    client_ip = get_client_ip(request)
    await check_rate_limit(
        key=f"ratelimit:search:{client_ip}",
        limit=60,
        window_seconds=60,
        error_msg="Limite de buscas por minuto excedido.",
    )

    offset = (page - 1) * limit

    # M4: Uso de CAST(:filter_type AS listing_type) em vez de :: colado ao bind param
    query = text("""
        SELECT * FROM get_nearby_businesses(
            :user_lat,
            :user_lng,
            :max_distance_km,
            :search_query,
            :filter_category,
            CAST(:filter_type AS listing_type),
            :page_limit,
            :page_offset,
            :filter_state,
            :filter_city
        );
    """)

    params = {
        "user_lat": lat,
        "user_lng": lng,
        "max_distance_km": radius_km,
        "search_query": q.strip() if q and q.strip() else None,
        "filter_category": category_id,
        "filter_type": listing_type if listing_type in ("service", "product", "both") else None,
        "page_limit": limit + 1,
        "page_offset": offset,
        "filter_state": state.upper().strip() if state and state.strip() else None,
        "filter_city": city.strip() if city and city.strip() else None,
    }

    result = await db.execute(query, params)
    rows = result.mappings().all()

    has_more = len(rows) > limit
    returned_rows = rows[:limit]

    items = []
    for r in returned_rows:
        item = dict(r)

        # H6: Ocultar telefones na listagem pública de cards (anti-scraping)
        item["whatsapp"] = None
        item["phone"] = None

        # Ocultar campos cadastrais de endereço se show_full_address for falso
        if not item.get("show_full_address"):
            item["street"] = None
            item["number"] = None

        # Flag semântica para UI
        item["serves_customer_location"] = (
            item.get("service_mode") in ("at_customer", "both")
        )
        items.append(item)

    return {
        "page": page,
        "limit": limit,
        "has_more": has_more,
        "total": len(items),
        "results": items,
    }
