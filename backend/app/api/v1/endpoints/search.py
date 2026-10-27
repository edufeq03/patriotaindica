import logging
from typing import Any, Dict, List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy import func, or_, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.database import get_db
from backend.app.core.rate_limit import check_rate_limit, get_client_ip
from backend.app.models.business import Business, BusinessCategory
from backend.app.models.category import Category

logger = logging.getLogger("patriotaindica.search")
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
    limit: int = Query(50, ge=1, le=100, description="Itens por página (máx 100)"),
    db: AsyncSession = Depends(get_db),
):
    """
    Busca nacional e por proximidade geográfica:
    - Retorna apenas empresas APROVADAS (status = 'approved').
    - Preserva WhatsApp para contato direto no marketplace.
    - Fallback resiliente com SQLAlchemy para garantir 100% de disponibilidade.
    """
    client_ip = get_client_ip(request)
    await check_rate_limit(
        key=f"ratelimit:search:{client_ip}",
        limit=60,
        window_seconds=60,
        error_msg="Limite de buscas por minuto excedido.",
    )

    offset = (page - 1) * limit
    items: List[Dict[str, Any]] = []
    has_more = False

    # 1. Tentar executar a função espacial get_nearby_businesses
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

    try:
        result = await db.execute(query, params)
        rows = result.mappings().all()

        has_more = len(rows) > limit
        returned_rows = rows[:limit]

        for r in returned_rows:
            item = dict(r)
            item["phone"] = None
            if not item.get("show_full_address"):
                item["street"] = None
                item["number"] = None

            item["serves_customer_location"] = (
                item.get("service_mode") in ("at_customer", "both")
            )
            item["status"] = "approved"

            if not item.get("category_slug") and item.get("category_name"):
                import re
                import unicodedata
                item["category_slug"] = re.sub(
                    r"[^a-z0-9]+",
                    "-",
                    unicodedata.normalize("NFKD", str(item["category_name"]))
                    .encode("ASCII", "ignore")
                    .decode("utf-8")
                    .lower(),
                ).strip("-")
            items.append(item)

    except Exception as err:
        logger.warning("get_nearby_businesses falhou ou não existe (%s). Executando fallback SQLAlchemy direto...", err)

        # Fallback ORM robusto direto na tabela businesses
        stmt = select(Business).where(Business.status == "approved")

        if listing_type and listing_type in ("service", "product", "both"):
            stmt = stmt.where(or_(Business.listing_type == listing_type, Business.listing_type == "both"))

        if state and state.strip():
            stmt = stmt.where(func.upper(Business.state) == state.upper().strip())

        if city and city.strip():
            stmt = stmt.where(Business.city.ilike(f"%{city.strip()}%"))

        if q and q.strip():
            search_str = f"%{q.strip()}%"
            stmt = stmt.where(
                or_(
                    Business.name.ilike(search_str),
                    Business.description.ilike(search_str),
                    Business.neighborhood.ilike(search_str),
                )
            )

        if category_id:
            stmt = stmt.join(BusinessCategory, BusinessCategory.business_id == Business.id).where(
                BusinessCategory.category_id == category_id
            )

        stmt = stmt.order_by(Business.is_verified.desc(), Business.created_at.desc()).offset(offset).limit(limit + 1)
        res = await db.execute(stmt)
        biz_list = res.scalars().all()

        has_more = len(biz_list) > limit
        returned_biz = biz_list[:limit]

        for b in returned_biz:
            cat_stmt = (
                select(Category.name, Category.slug)
                .join(BusinessCategory, BusinessCategory.category_id == Category.id)
                .where(BusinessCategory.business_id == b.id)
            )
            cat_row = (await db.execute(cat_stmt)).first()
            c_name = cat_row[0] if cat_row else "Serviços"
            c_slug = cat_row[1] if cat_row else "servicos"

            item = {
                "id": str(b.id),
                "name": b.name,
                "slug": b.slug,
                "description": b.description,
                "listing_type": b.listing_type,
                "service_mode": b.service_mode,
                "service_radius_km": b.service_radius_km,
                "category_name": c_name,
                "category_slug": c_slug,
                "whatsapp": b.whatsapp,
                "phone": None,
                "neighborhood": b.neighborhood,
                "city": b.city,
                "state": b.state,
                "street": b.street if b.show_full_address else None,
                "number": b.number if b.show_full_address else None,
                "show_full_address": b.show_full_address,
                "logo_url": b.logo_url,
                "banner_url": b.banner_url,
                "is_verified": b.is_verified,
                "distance_km": None,
                "status": "approved",
                "serves_customer_location": b.service_mode in ("at_customer", "both"),
            }
            items.append(item)

    return {
        "page": page,
        "limit": limit,
        "has_more": has_more,
        "total": len(items),
        "results": items,
    }
