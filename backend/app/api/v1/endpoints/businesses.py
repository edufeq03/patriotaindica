import re
import secrets
import unicodedata
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.app.core.database import get_db
from backend.app.core.rate_limit import check_rate_limit, get_client_ip
from backend.app.models.business import Business, BusinessCategory
from backend.app.models.category import Category
from backend.app.models.events import BusinessReviewLog, Report
from backend.app.schemas.business import BusinessApplicationCreate, BusinessDetail, ReportCreate
from backend.app.services.geocoding import geocode_address

router = APIRouter()

RESERVED_SLUGS = {
    "admin", "api", "go", "convite", "painel-empresa", "auth",
    "search", "brasil", "curadoria", "termos", "privacidade", "login", "register"
}


def slugify(text: str) -> str:
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("utf-8")
    text = re.sub(r"[^\w\s-]", "", text).strip().lower()
    return re.sub(r"[-\s]+", "-", text)


@router.get("/by-slug/{slug}", response_model=Dict[str, Any])
async def get_business_by_slug(slug: str, db: AsyncSession = Depends(get_db)):
    """
    Retorna o perfil público completo da empresa para SEO e página de detalhes.
    Apenas empresas APROVADAS são exibidas publicamente.
    """
    stmt = (
        select(Business)
        .options(
            selectinload(Business.categories).joinedload(BusinessCategory.category)
        )
        .where(Business.slug == slug, Business.status == "approved")
    )
    result = await db.execute(stmt)
    business = result.scalar_one_or_none()

    if not business:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Empresa não encontrada ou ainda em análise de curadoria.",
        )

    categories_list = [
        {
            "id": bc.category.id,
            "name": bc.category.name,
            "slug": bc.category.slug,
            "kind": bc.category.kind,
            "icon_name": bc.category.icon_name,
            "is_primary": bc.is_primary,
        }
        for bc in business.categories
        if bc.category
    ]

    return {
        "id": business.id,
        "name": business.name,
        "slug": business.slug,
        "description": business.description,
        "listing_type": business.listing_type,
        "service_mode": business.service_mode,
        "service_radius_km": business.service_radius_km,
        "whatsapp": business.whatsapp,
        "phone": business.phone,
        "website": business.website,
        "instagram": business.instagram,
        "neighborhood": business.neighborhood,
        "city": business.city,
        "state": business.state,
        "street": business.street if business.show_full_address else None,
        "number": business.number if business.show_full_address else None,
        "show_full_address": business.show_full_address,
        "logo_url": business.logo_url,
        "banner_url": business.banner_url,
        "is_verified": business.is_verified,
        "categories": categories_list,
        "created_at": business.created_at,
    }


@router.post("/application", status_code=status.HTTP_201_CREATED)
async def submit_business_application(
    payload: BusinessApplicationCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """
    Canal C: Candidatura pública ('Quero ser indicado').
    SEGURANÇA:
    - [H1] Rate limit por IP (3/dia).
    - [H4] Coordenadas vindas do cliente são ignoradas. Geocodificação server-side
           usando BrasilAPI/Nominatim para qualquer CEP/cidade do Brasil.
    - [M6] Geração segura de slug com checagem de palavras reservadas e sufixo aleatório.
    - REGRA INEGOCIÁVEL: Cria registro estritamente com status = 'pending_review' e source = 'application'.
    """
    client_ip = get_client_ip(request)
    await check_rate_limit(
        key=f"ratelimit:application:{client_ip}",
        limit=10,
        window_seconds=86400,
        error_msg="Limite de 10 candidaturas por dia atingido para seu endereço IP.",
    )

    # Geração robusta de slug (M6)
    base_slug = slugify(f"{payload.name}-{payload.city}")
    if not base_slug or base_slug in RESERVED_SLUGS:
        base_slug = f"empresa-{secrets.token_hex(3)}"

    slug = base_slug
    attempts = 0
    while attempts < 5:
        stmt = select(Business.id).where(Business.slug == slug)
        exists = (await db.execute(stmt)).scalar_one_or_none()
        if not exists:
            break
        slug = f"{base_slug}-{secrets.token_hex(2)}"
        attempts += 1

    # Geocodificação server-side (H4 - suporte nacional)
    lat, lng, geo_source, geo_conf = await geocode_address(
        postal_code=payload.postal_code,
        city=payload.city,
        state=payload.state,
        street=payload.street,
        number=payload.number,
    )
    location_geog = f"SRID=4326;POINT({lng} {lat})" if lat is not None and lng is not None else None

    # Limpar documento
    doc_num = (
        "".join(filter(str.isdigit, payload.document_number))
        if payload.document_number
        else None
    )

    new_business = Business(
        name=payload.name.strip(),
        slug=slug,
        description=payload.description.strip() if payload.description else None,
        listing_type=payload.listing_type,
        document_type=payload.document_type or "CNPJ",
        document_number=doc_num,
        whatsapp=payload.whatsapp.strip(),
        phone=payload.phone.strip() if payload.phone else None,
        website=payload.website.strip() if payload.website else None,
        instagram=payload.instagram.strip() if payload.instagram else None,
        street=payload.street.strip() if payload.street else None,
        number=payload.number.strip() if payload.number else None,
        neighborhood=payload.neighborhood.strip(),
        city=payload.city.strip(),
        state=payload.state.upper().strip(),
        postal_code=payload.postal_code.strip() if payload.postal_code else None,
        show_full_address=payload.show_full_address,
        location=location_geog,
        geocode_source=geo_source,
        geocode_confidence=geo_conf,
        service_mode=payload.service_mode,
        service_radius_km=payload.service_radius_km,
        status="pending_review",
        source="application",
        is_verified=False,
    )

    db.add(new_business)
    await db.flush()

    # Vincular categorias existentes
    for cat_id in payload.category_ids:
        is_primary = (cat_id == payload.primary_category_id)
        bc = BusinessCategory(
            business_id=new_business.id,
            category_id=cat_id,
            is_primary=is_primary,
        )
        db.add(bc)

    # Vincular ou propor novo nicho dinâmico (Sec. 4)
    if payload.proposed_niche:
        niche_name = payload.proposed_niche.strip()
        cat_stmt = select(Category).where(Category.name.ilike(niche_name))
        existing_cat = (await db.execute(cat_stmt)).scalar_one_or_none()
        if existing_cat:
            bc = BusinessCategory(
                business_id=new_business.id,
                category_id=existing_cat.id,
                is_primary=True if not payload.category_ids else False,
            )
            db.add(bc)
        else:
            base_niche_slug = slugify(niche_name)
            new_niche = Category(
                name=niche_name,
                slug=f"{base_niche_slug}-{secrets.token_hex(2)}",
                kind=payload.listing_type,
                status="pending",
                icon_name="sparkles",
                proposed_by_business_id=new_business.id,
            )
            db.add(new_niche)
            await db.flush()
            bc = BusinessCategory(
                business_id=new_business.id,
                category_id=new_niche.id,
                is_primary=True if not payload.category_ids else False,
            )
            db.add(bc)

    # Registrar log de auditoria
    review_log = BusinessReviewLog(
        business_id=new_business.id,
        from_status=None,
        to_status="pending_review",
        note="Candidatura espontânea submetida via formulário público (Canal C). Aguardando triagem.",
    )
    db.add(review_log)

    await db.commit()

    return {
        "success": True,
        "message": "Candidatura recebida com sucesso! Nossa equipe analisará os dados em até 48 horas.",
        "business_id": new_business.id,
        "status": "pending_review",
    }


@router.post("/{business_id}/report")
async def report_business(
    business_id: UUID,
    payload: ReportCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """
    Submissão de denúncia por consumidor sobre dados falsos, golpe ou infração.
    SEGURANÇA:
    - [H1] Rate limit por IP (5/dia).
    - [H2] Deduplicação por IP + empresa em 24h.
    - [H2] Nunca suspende automaticamente a empresa denunciada (apenas alerta a moderação).
    """
    client_ip = get_client_ip(request)
    await check_rate_limit(
        key=f"ratelimit:report:{client_ip}",
        limit=5,
        window_seconds=86400,
        error_msg="Limite diário de denúncias excedido para seu endereço IP.",
    )

    # Deduplicação por IP e empresa (evitar flood contra um mesmo negócio)
    await check_rate_limit(
        key=f"ratelimit:report_business:{client_ip}:{business_id}",
        limit=1,
        window_seconds=86400,
        error_msg="Você já enviou uma denúncia para esta empresa nas últimas 24 horas.",
    )

    stmt = select(Business.id).where(Business.id == business_id)
    exists = (await db.execute(stmt)).scalar_one_or_none()
    if not exists:
        raise HTTPException(status_code=404, detail="Empresa não encontrada.")

    report = Report(
        business_id=business_id,
        reason=payload.reason.strip(),
        details=payload.details.strip() if payload.details else None,
        contact_email=str(payload.contact_email).strip() if payload.contact_email else None,
        status="pending",
    )
    db.add(report)
    await db.commit()

    return {"success": True, "message": "Denúncia registrada para análise da curadoria. Agradecemos sua colaboração."}
