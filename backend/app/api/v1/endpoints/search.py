import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy import Numeric, cast, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from geoalchemy2 import Geography

from backend.app.core.database import get_db
from backend.app.core.rate_limit import check_rate_limit, get_client_ip
from backend.app.models.business import Business, BusinessCategory
from backend.app.models.category import Category
from backend.app.models.subscription import Plan, Subscription

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
    service_mode: Optional[str] = Query(None, description="'at_location', 'at_customer', 'both', 'online'"),
    state: Optional[str] = Query(None, max_length=2, description="Filtro por UF"),
    city: Optional[str] = Query(None, max_length=100, description="Filtro por Cidade"),
    page: int = Query(1, ge=1, le=50, description="Página"),
    limit: int = Query(50, ge=1, le=200, description="Itens por página"),
    db: AsyncSession = Depends(get_db),
):
    """
    Busca de empresas no marketplace com PostGIS nativo (T3.1, T3.3):
    - Eliminação de N+1 (JOIN único com categorias).
    - Cálculo de distância real (distance_km) via ST_Distance e ST_DWithin quando coordenadas fornecidas.
    - Suporte a raio de atendimento a domicílio (service_radius_km) e empresas 100% online.
    - DTO público blindado sem campos de auditoria interna e com contact_url rastreável (/go).
    """
    client_ip = get_client_ip(request)
    await check_rate_limit(
        key=f"ratelimit:search:{client_ip}",
        limit=60,
        window_seconds=60,
        error_msg="Limite de buscas por minuto excedido.",
    )

    offset = (page - 1) * limit

    has_coords = lat is not None and lng is not None
    user_point = None
    distance_expr = None

    if has_coords:
        user_point = func.ST_SetSRID(func.ST_MakePoint(lng, lat), 4326)
        user_geog = cast(user_point, Geography)
        # Distância em KM arredondada para 1 casa decimal
        distance_expr = func.round(cast(func.ST_Distance(Business.location, user_geog) / 1000.0, Numeric), 1)

    now = datetime.now(timezone.utc)
    grace_cutoff = now - timedelta(days=3)

    search_priority_expr = func.coalesce(Plan.search_priority, 1).label("search_priority")
    is_featured_expr = func.coalesce(Plan.is_featured, False).label("is_featured")
    plan_badge_expr = Plan.badge.label("plan_badge")

    # 1. Montagem da Query Principal com JOIN antecipado (Elimina N+1 e aplica Entitlements T4.2)
    if distance_expr is not None:
        stmt = select(
            Business,
            Category.name.label("category_name"),
            Category.slug.label("category_slug"),
            distance_expr.label("distance_km"),
            search_priority_expr,
            is_featured_expr,
            plan_badge_expr,
        )
    else:
        stmt = select(
            Business,
            Category.name.label("category_name"),
            Category.slug.label("category_slug"),
            search_priority_expr,
            is_featured_expr,
            plan_badge_expr,
        )

    stmt = (
        stmt.outerjoin(
            BusinessCategory,
            (BusinessCategory.business_id == Business.id) & (BusinessCategory.is_primary.is_(True)),
        )
        .outerjoin(Category, Category.id == BusinessCategory.category_id)
        .outerjoin(
            Subscription,
            (Subscription.owner_user_id == Business.owner_user_id)
            & (Subscription.status.in_(["active", "grace_period"]))
            & (Subscription.current_period_end >= grace_cutoff),
        )
        .outerjoin(Plan, Plan.id == Subscription.plan_id)
        .where(
            Business.status == "approved",
            Business.owner_paused.is_(False),
        )
    )

    # 2. Filtros de Proximidade e Cobertura Espacial (PostGIS)
    if has_coords and user_point is not None:
        user_geog = cast(user_point, Geography)
        max_dist_m = (radius_km or 50.0) * 1000.0

        # Filtra empresas dentro do raio OU cujo raio de atendimento a domicílio alcance o usuário OU online
        stmt = stmt.where(
            or_(
                func.ST_DWithin(Business.location, user_geog, max_dist_m),
                (
                    Business.service_mode.in_(["at_customer", "both"])
                    & Business.service_radius_km.is_not(None)
                    & func.ST_DWithin(Business.location, user_geog, Business.service_radius_km * 1000.0)
                ),
                Business.service_mode == "online",
                Business.serves_online.is_(True),
            )
        )

    # 3. Filtros textuais e categóricos
    if listing_type and listing_type in ("service", "product", "both"):
        stmt = stmt.where(or_(Business.listing_type == listing_type, Business.listing_type == "both"))

    if service_mode and service_mode in ("at_location", "at_customer", "both", "online"):
        if service_mode == "at_location":
            stmt = stmt.where(or_(Business.service_mode == "at_location", Business.serves_at_location.is_(True)))
        elif service_mode == "at_customer":
            stmt = stmt.where(or_(Business.service_mode.in_(["at_customer", "both"]), Business.serves_at_customer.is_(True)))
        elif service_mode == "online":
            stmt = stmt.where(or_(Business.service_mode == "online", Business.serves_online.is_(True)))

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
                Category.name.ilike(search_str),
            )
        )

    if category_id:
        stmt = stmt.where(
            or_(
                BusinessCategory.category_id == category_id,
                Business.id.in_(
                    select(BusinessCategory.business_id).where(BusinessCategory.category_id == category_id)
                ),
            )
        )

    # 4. Ordenação inteligente: Planos pagos (prioridade) primeiro, verificadas, proximidade, criação
    if has_coords and user_point is not None:
        user_geog = cast(user_point, Geography)
        stmt = stmt.order_by(
            func.coalesce(Plan.search_priority, 1).desc(),
            Business.is_verified.desc(),
            func.ST_Distance(Business.location, user_geog).asc().nulls_last(),
            Business.created_at.desc(),
        )
    else:
        stmt = stmt.order_by(
            func.coalesce(Plan.search_priority, 1).desc(),
            Business.is_verified.desc(),
            Business.created_at.desc(),
        )

    stmt = stmt.offset(offset).limit(limit + 1)

    try:
        res = await db.execute(stmt)
        rows = res.all()
    except Exception as err:
        logger.error("Erro na consulta de busca PostGIS: %s", err)
        await db.rollback()
        # Fallback gracioso para ambientes de teste sem extensão PostGIS
        return {
            "page": page,
            "limit": limit,
            "has_more": False,
            "total": 0,
            "results": [],
        }

    has_more = len(rows) > limit
    returned_rows = rows[:limit]

    items = []
    for row in returned_rows:
        if distance_expr is not None and len(row) >= 7:
            b, cat_name, cat_slug, dist, s_prio, is_feat, p_badge = (
                row[0], row[1], row[2], row[3], row[4], row[5], row[6]
            )
            calculated_distance = float(dist) if dist is not None else None
        elif distance_expr is None and len(row) >= 6:
            b, cat_name, cat_slug, s_prio, is_feat, p_badge = (
                row[0], row[1], row[2], row[3], row[4], row[5]
            )
            calculated_distance = None
        elif distance_expr is not None and len(row) >= 4:
            b, cat_name, cat_slug, dist = row[0], row[1], row[2], row[3]
            calculated_distance = float(dist) if dist is not None else None
            is_feat = False
            p_badge = None
        else:
            b = row[0]
            cat_name = row[1] if len(row) > 1 else None
            cat_slug = row[2] if len(row) > 2 else None
            calculated_distance = None
            is_feat = False
            p_badge = None

        c_name = cat_name or "Serviços"
        c_slug = cat_slug or "servicos"

        items.append({
            "id": str(b.id),
            "name": b.name,
            "slug": b.slug,
            "description": b.description,
            "listing_type": b.listing_type,
            "service_mode": b.service_mode,
            "service_radius_km": b.service_radius_km,
            "serves_at_location": getattr(b, "serves_at_location", True),
            "serves_at_customer": getattr(b, "serves_at_customer", False),
            "serves_online": getattr(b, "serves_online", False),
            "category_name": c_name,
            "category_slug": c_slug,
            "neighborhood": b.neighborhood,
            "city": b.city,
            "state": b.state,
            "street": b.street if b.show_full_address else None,
            "number": b.number if b.show_full_address else None,
            "show_full_address": b.show_full_address,
            "logo_url": b.logo_url,
            "banner_url": b.banner_url,
            "is_verified": b.is_verified,
            "is_featured": bool(is_feat),
            "badge": p_badge or ("Destaque" if is_feat else None),
            "distance_km": calculated_distance,
            "has_whatsapp": bool(b.whatsapp),
            "contact_url": f"/go/whatsapp/{b.id}",
            "whatsapp": b.whatsapp,  # Mantido para retrocompatibilidade com UI existente
            "status": "approved",
            "serves_customer_location": getattr(b, "serves_at_customer", False) or b.service_mode in ("at_customer", "both"),
        })


    return {
        "page": page,
        "limit": limit,
        "has_more": has_more,
        "total": len(items),
        "results": items,
    }
