import re
import unicodedata
from typing import Any, Dict, List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from backend.app.core.database import get_db
from backend.app.models.business import Business, BusinessCategory
from backend.app.models.category import Category
from backend.app.models.events import BusinessReviewLog, Report
from backend.app.schemas.business import BusinessApplicationCreate, BusinessDetail

router = APIRouter()


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
    db: AsyncSession = Depends(get_db),
):
    """
    Canal C: Candidatura pública ('Quero ser indicado').
    REGRA INEGOCIÁVEL: NÃO publica nada diretamente.
    Cria registro estritamente com status = 'pending_review' e source = 'application'.
    """
    base_slug = slugify(f"{payload.name}-{payload.city}")
    # Garantir unicidade de slug
    slug = base_slug
    counter = 1
    while True:
        stmt = select(Business.id).where(Business.slug == slug)
        exists = (await db.execute(stmt)).scalar_one_or_none()
        if not exists:
            break
        slug = f"{base_slug}-{counter}"
        counter += 1

    # Coordenadas padrão (fallback para centro da cidade se não informado)
    lat = payload.latitude if payload.latitude is not None else -22.9056
    lng = payload.longitude if payload.longitude is not None else -47.0608
    location_geog = f"SRID=4326;POINT({lng} {lat})"

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
        listing_type="service",
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
        service_mode=payload.service_mode,
        service_radius_km=payload.service_radius_km,
        status="pending_review",
        source="application",
        is_verified=False,
    )

    db.add(new_business)
    await db.flush()

    # Vincular categorias
    for cat_id in payload.category_ids:
        is_primary = (cat_id == payload.primary_category_id)
        bc = BusinessCategory(
            business_id=new_business.id,
            category_id=cat_id,
            is_primary=is_primary,
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
    reason: str,
    details: Optional[str] = None,
    contact_email: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    """
    Submissão de denúncia por consumidor sobre dados falsos, golpe ou infração.
    """
    stmt = select(Business.id).where(Business.id == business_id)
    exists = (await db.execute(stmt)).scalar_one_or_none()
    if not exists:
        raise HTTPException(status_code=404, detail="Empresa não encontrada.")

    report = Report(
        business_id=business_id,
        reason=reason,
        details=details,
        contact_email=contact_email,
        status="pending",
    )
    db.add(report)
    await db.commit()

    return {"success": True, "message": "Denúncia registrada. Agradecemos sua colaboração."}
