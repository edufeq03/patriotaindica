import logging
from typing import Any, Dict, List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy import func, or_, select
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
    lat: Optional[float] = Query(None, ge=-90.0, le=90.0, description="Latitude do usuário (opcional)"),
    lng: Optional[float] = Query(None, ge=-180.0, le=180.0, description="Longitude do usuário (opcional)"),
    radius_km: Optional[float] = Query(None, ge=1.0, le=500.0, description="Raio de busca em km (opcional)"),
    q: Optional[str] = Query(None, max_length=80, description="Busca textual"),
    category_id: Optional[UUID] = Query(None, description="Filtro por categoria"),
    listing_type: Optional[str] = Query(None, description="'service', 'product', ou 'both'"),
    state: Optional[str] = Query(None, max_length=2, description="Filtro por UF"),
    city: Optional[str] = Query(None, max_length=100, description="Filtro por Cidade"),
    page: int = Query(1, ge=1, le=50, description="Página"),
    limit: int = Query(50, ge=1, le=200, description="Itens por página"),
    db: AsyncSession = Depends(get_db),
):
    """
    Busca de empresas no marketplace (100% resiliente):
    - Retorna empresas APROVADAS (status = 'approved').
    - Preserva WhatsApp para contato direto no marketplace.
    - Suporta busca nacional, por texto, cidade, estado e categoria sem dependência de stored procedures externas.
    """
    client_ip = get_client_ip(request)
    await check_rate_limit(
        key=f"ratelimit:search:{client_ip}",
        limit=60,
        window_seconds=60,
        error_msg="Limite de buscas por minuto excedido.",
    )

    offset = (page - 1) * limit

    # Query principal diretamente na tabela businesses
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
                Business.city.ilike(search_str),
            )
        )

    if category_id:
        stmt = stmt.join(BusinessCategory, BusinessCategory.business_id == Business.id).where(
            BusinessCategory.category_id == category_id
        )

    # Ordenar por verificadas primeiro, depois data de criação mais recente
    stmt = stmt.order_by(Business.is_verified.desc(), Business.created_at.desc()).offset(offset).limit(limit + 1)

    try:
        res = await db.execute(stmt)
        biz_list = res.scalars().all()
    except Exception as err:
        logger.error("Erro na consulta de busca: %s", err)
        await db.rollback()
        return {
            "page": page,
            "limit": limit,
            "has_more": False,
            "total": 0,
            "results": [],
        }

    has_more = len(biz_list) > limit
    returned_biz = biz_list[:limit]

    items = []
    for b in returned_biz:
        # Categoria vinculada
        cat_stmt = (
            select(Category.name, Category.slug)
            .join(BusinessCategory, BusinessCategory.category_id == Category.id)
            .where(BusinessCategory.business_id == b.id)
        )
        cat_res = await db.execute(cat_stmt)
        cat_row = cat_res.first()
        c_name = cat_row[0] if cat_row else "Serviços"
        c_slug = cat_row[1] if cat_row else "servicos"

        items.append({
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
        })

    return {
        "page": page,
        "limit": limit,
        "has_more": has_more,
        "total": len(items),
        "results": items,
    }


@router.get("/audit", tags=["Audit"])
async def audit_approved_businesses(
    db: AsyncSession = Depends(get_db),
):
    """
    Endpoint leve de auditoria: lista todas as empresas com seus status para diagnóstico.
    """
    stmt = select(Business.id, Business.name, Business.status, Business.city, Business.state, Business.created_at).order_by(Business.created_at.desc()).limit(20)
    res = await db.execute(stmt)
    rows = res.all()
    return {
        "total_returned": len(rows),
        "businesses": [
            {
                "id": str(r[0]),
                "name": r[1],
                "status": r[2],
                "city": r[3],
                "state": r[4],
                "created_at": r[5].isoformat() if r[5] else None,
            }
            for r in rows
        ],
    }
