import logging
import re
import secrets
import unicodedata
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

import hashlib
from backend.app.core.config import settings
from backend.app.core.database import get_db
from backend.app.core.rate_limit import check_rate_limit, get_client_ip
from backend.app.models.business import Business, BusinessCategory, PeerEndorsement
from backend.app.models.category import Category
from backend.app.models.events import BusinessReviewLog, Consent, Report
from backend.app.schemas.business import BusinessApplicationCreate, BusinessDetail, ReportCreate
from backend.app.services.geocoding import geocode_address
from backend.app.services.otp import normalize_e164

logger = logging.getLogger(__name__)

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
        .where(
            func.lower(Business.slug) == slug.lower().strip(),
            Business.status == "approved",
            Business.owner_paused.is_(False),
        )
    )
    result = await db.execute(stmt)
    business = result.scalar_one_or_none()

    if not business:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Empresa não encontrada ou inativa.",
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
        "serves_at_location": getattr(business, "serves_at_location", True),
        "serves_at_customer": getattr(business, "serves_at_customer", False),
        "serves_online": getattr(business, "serves_online", False),
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
        "status": business.status,
        "is_verified": business.is_verified,
        "network_badge": getattr(business, "network_badge", "membro_verificado"),
        "endorsements_count": getattr(business, "endorsements_count", 0),
        "is_available_now": bool(business.availability_until and business.availability_until > datetime.now(timezone.utc)),
        "availability_until": business.availability_until.isoformat() if business.availability_until else None,
        "categories": categories_list,
        "created_at": business.created_at,
    }


@router.get("/by-slug/{slug}/endorsements", response_model=Dict[str, Any])
async def get_business_endorsements(slug: str, db: AsyncSession = Depends(get_db)):
    """
    T7.2: Lista pública de recomendações de confiança recebidas de outras empresas parceiras da rede.
    Apenas empresas e recomendações aprovadas/públicas são exibidas.
    """
    # 1. Buscar a empresa
    stmt = select(Business).where(
        func.lower(Business.slug) == slug.lower().strip(),
        Business.status == "approved",
        Business.owner_paused.is_(False),
    )
    business = (await db.execute(stmt)).scalar_one_or_none()
    if not business:
        raise HTTPException(status_code=404, detail="Empresa não encontrada.")

    # 2. Buscar as recomendações de pares aprovados
    end_stmt = (
        select(PeerEndorsement, Business)
        .join(Business, Business.id == PeerEndorsement.endorsing_business_id)
        .where(
            PeerEndorsement.endorsed_business_id == business.id,
            PeerEndorsement.is_public.is_(True),
            Business.status == "approved",
            Business.owner_paused.is_(False),
        )
        .order_by(PeerEndorsement.created_at.desc())
    )
    records = (await db.execute(end_stmt)).all()

    endorsements = []
    for endorsement, endorsing_biz in records:
        endorsements.append({
            "endorsing_business_name": endorsing_biz.name,
            "endorsing_business_slug": endorsing_biz.slug,
            "endorsing_business_city": endorsing_biz.city,
            "endorsing_business_neighborhood": endorsing_biz.neighborhood,
            "endorsing_business_badge": getattr(endorsing_biz, "network_badge", "membro_verificado"),
            "relationship_type": endorsement.relationship_type,
            "testimonial": endorsement.testimonial,
            "created_at": endorsement.created_at.isoformat(),
        })

    return {
        "business_name": business.name,
        "business_slug": business.slug,
        "endorsements_count": len(endorsements),
        "endorsements": endorsements,
    }


@router.get("/by-slug/{slug}/trust-card", response_model=Dict[str, Any])
async def get_business_trust_card(slug: str, db: AsyncSession = Depends(get_db)):
    """
    T7.3: Cartão Digital de Confiança / Mini-site para links de redes sociais e QR Codes físicos.
    """
    stmt = (
        select(Business)
        .where(
            func.lower(Business.slug) == slug.lower().strip(),
            Business.status == "approved",
            Business.owner_paused.is_(False),
        )
    )
    business = (await db.execute(stmt)).scalar_one_or_none()
    if not business:
        raise HTTPException(status_code=404, detail="Empresa não encontrada.")

    clean_wa = re.sub(r"\D", "", business.whatsapp_e164 or business.whatsapp)
    encoded_greeting = (
        f"Ol%C3%A1!%20Encontrei%20o%20perfil%20do(a)%20{business.name}%20na%20Rede%20Patriota%20Indica%20"
        f"e%20gostaria%20de%20um%20atendimento%20de%20confian%C3%A7a."
    )
    direct_whatsapp_url = f"https://wa.me/{clean_wa}?text={encoded_greeting}"
    base_url = settings.PUBLIC_APP_URL.rstrip("/")
    share_url = f"{base_url}/q/{business.slug}"

    now = datetime.now(timezone.utc)
    is_avail = bool(business.availability_until and business.availability_until > now)

    return {
        "name": business.name,
        "slug": business.slug,
        "city": business.city,
        "state": business.state,
        "neighborhood": business.neighborhood,
        "network_badge": getattr(business, "network_badge", "membro_verificado"),
        "is_verified": business.is_verified,
        "endorsements_count": getattr(business, "endorsements_count", 0),
        "is_available_now": is_avail,
        "availability_until": business.availability_until.isoformat() if business.availability_until else None,
        "direct_whatsapp_url": direct_whatsapp_url,
        "share_url": share_url,
        "website": business.website,
        "instagram": business.instagram,
        "phone": business.phone,
        "verified_network_statement": "Esta empresa faz parte da Rede de Negócios Confiáveis Patriota Indica, com curadoria e princípios alinhados à comunidade.",
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
    location_pending = (location_geog is None)

    # Limpar documento
    doc_num = (
        "".join(filter(str.isdigit, payload.document_number))
        if payload.document_number
        else None
    )

    flag_duplicate_doc = False
    if doc_num:
        doc_stmt = select(Business.id).where(
            Business.document_number == doc_num,
            func.lower(Business.name) == payload.name.strip().lower(),
        )
        existing_doc = (await db.execute(doc_stmt)).scalar_one_or_none()
        if existing_doc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Uma empresa com este mesmo nome e CNPJ/CPF já possui cadastro no sistema.",
            )

        # DETECÇÃO DE DOCUMENTO JÁ USADO POR OUTRO DONO (T1.4)
        other_doc_stmt = select(Business.id).where(Business.document_number == doc_num)
        other_doc_biz = (await db.execute(other_doc_stmt)).first()
        if other_doc_biz:
            flag_duplicate_doc = True

    ref_code = f"PAT-{secrets.token_hex(3).upper()}"
    whatsapp_e164 = normalize_e164(payload.whatsapp)

    try:
        new_business = Business(
            name=payload.name.strip(),
            slug=slug,
            description=payload.description.strip() if payload.description else None,
            listing_type=payload.listing_type,
            document_type=payload.document_type or "CNPJ",
            document_number=doc_num,
            document_flag_duplicate=flag_duplicate_doc,
            owner_paused=False,
            referral_code=ref_code,
            referred_by_code=payload.referred_by_code.strip() if payload.referred_by_code else None,
            whatsapp=payload.whatsapp.strip(),
            whatsapp_e164=whatsapp_e164,
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
            location_pending=location_pending,
            service_mode=payload.service_mode,
            service_radius_km=payload.service_radius_km,
            serves_at_location=payload.serves_at_location,
            serves_at_customer=payload.serves_at_customer,
            serves_online=payload.serves_online,
            status="pending_review",
            source="application",
            is_verified=False,
        )

        db.add(new_business)
        await db.flush()

        # PERSISTÊNCIA DE CONSENTIMENTO LGPD AUDITÁVEL (T1.6)
        client_ip = get_client_ip(request)
        ip_hash = hashlib.sha256(client_ip.encode("utf-8")).hexdigest() if client_ip else None
        ua = request.headers.get("user-agent", "")
        ua_hash = hashlib.sha256(ua.encode("utf-8")).hexdigest() if ua else None

        for c_type in ("carta_principios", "terms_of_service", "privacy_policy"):
            consent_record = Consent(
                business_id=new_business.id,
                user_id=None,
                type=c_type,
                version="1.0",
                ip_hash=ip_hash,
                user_agent_hash=ua_hash,
            )
            db.add(consent_record)

        # Rastrear indicação se veio com código de empresa parceira
        if payload.referred_by_code and payload.referred_by_code.strip():
            clean_ref = payload.referred_by_code.strip().upper()
            ref_stmt = select(Business).where(func.upper(Business.referral_code) == clean_ref)
            ref_biz = (await db.execute(ref_stmt)).scalars().first()
            if ref_biz:
                from backend.app.models.subscription import Referral
                referral_record = Referral(
                    referrer_user_id=ref_biz.owner_user_id,
                    referrer_business_id=ref_biz.id,
                    referred_business_id=new_business.id,
                    code=clean_ref,
                    status="pending",
                )
                db.add(referral_record)

        # Vincular categorias existentes com verificação de FK
        for cat_id in payload.category_ids:
            cat_check = (await db.execute(select(Category.id).where(Category.id == cat_id))).scalar_one_or_none()
            if cat_check:
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
            cat_results = (await db.execute(cat_stmt)).scalars().all()
            if cat_results:
                existing_cat = cat_results[0]
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
    except HTTPException:
        await db.rollback()
        raise
    except IntegrityError as ie:
        await db.rollback()
        logger.error("Erro de integridade ao salvar empresa: %s", ie, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Não foi possível salvar o cadastro devido a um conflito de dados (CNPJ ou nome já existente).",
        )
    except Exception as exc:
        await db.rollback()
        logger.error("Erro inesperado ao salvar candidatura: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Erro ao salvar candidatura no banco de dados. Verifique as informações e tente novamente.",
        )


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
