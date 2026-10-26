from typing import Any, Dict, List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, Query
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from backend.app.core.database import get_db

router = APIRouter()


@router.get("", response_model=Dict[str, Any])
async def search_nearby_businesses(
    lat: float = Query(..., description="Latitude do usuário"),
    lng: float = Query(..., description="Longitude do usuário"),
    radius_km: float = Query(50.0, description="Raio de busca em km"),
    q: Optional[str] = Query(None, description="Busca textual (nome ou especialidade)"),
    category_id: Optional[UUID] = Query(None, description="Filtro por categoria"),
    listing_type: Optional[str] = Query(None, description="'service', 'product', ou 'both'"),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """
    Busca inteligente por proximidade geográfica e área de atendimento usando PostGIS.
    Garante:
    1. Apenas empresas aprovadas (status = 'approved').
    2. Respeita raio atendido para serviços a domicílio (service_radius_km).
    3. Ordenação por proximidade usando índice espacial GIST e operador KNN (<->).
    4. Busca textual fonética e sem acento em português.
    """
    offset = (page - 1) * limit

    query = text("""
        SELECT * FROM get_nearby_businesses(
            :user_lat,
            :user_lng,
            :max_distance_km,
            :search_query,
            :filter_category,
            :filter_type::listing_type,
            :page_limit,
            :page_offset
        );
    """)

    params = {
        "user_lat": lat,
        "user_lng": lng,
        "max_distance_km": radius_km,
        "search_query": q if q and q.strip() else None,
        "filter_category": category_id,
        "filter_type": listing_type if listing_type in ("service", "product", "both") else None,
        "page_limit": limit + 1,  # Busca 1 a mais para saber se tem próxima página
        "page_offset": offset,
    }

    result = await db.execute(query, params)
    rows = result.mappings().all()

    has_more = len(rows) > limit
    returned_rows = rows[:limit]

    items = []
    for r in returned_rows:
        item = dict(r)
        # Ocultar campos cadastrais de endereço se show_full_address for falso
        if not item.get("show_full_address"):
            item["street"] = None
            item["number"] = None

        # Adicionar flag semântica para UI
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
