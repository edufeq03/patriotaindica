import hashlib
import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.app.core.config import settings
from backend.app.core.database import get_db
from backend.app.core.rate_limit import check_rate_limit, get_client_ip
from backend.app.models.business import Business, BusinessCategory
from backend.app.models.category import Category
from backend.app.models.jobs import JobOpening, JobReport, JobReviewLog
from backend.app.schemas.jobs import JobReportCreate, PublicJobCard

logger = logging.getLogger("patriotaindica.public_jobs")
router = APIRouter()


def get_ip_hash(ip: str) -> str:
    salt = getattr(settings, "SECRET_KEY", "patriotaindica_default_salt")
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    raw = f"{ip}:{salt}:{today}".encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


@router.get("", response_model=Dict[str, Any])
async def list_public_jobs(
    request: Request,
    city: Optional[str] = Query(None, max_length=100),
    state: Optional[str] = Query(None, max_length=2),
    category_id: Optional[UUID] = Query(None),
    contract_type: Optional[str] = Query(None),
    business_id: Optional[UUID] = Query(None),
    q: Optional[str] = Query(None, max_length=60),
    page: int = Query(1, ge=1, le=50),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """
    Lista vagas de emprego ativas e públicas com paginação e filtros.
    Cumpre estritamente as regras de visibilidade pública (Seção 4).
    """
    client_ip = get_client_ip(request)
    await check_rate_limit(
        key=f"ratelimit:jobs_list:{client_ip}",
        limit=60,
        window_seconds=60,
        error_msg="Muitas requisições de vagas. Aguarde um instante.",
    )

    now = datetime.now(timezone.utc)
    offset = (page - 1) * limit

    # Regra estrita de visibilidade pública (Seção 4)
    stmt = (
        select(
            JobOpening,
            Business.id.label("b_id"),
            Business.name.label("b_name"),
            Business.slug.label("b_slug"),
            Business.city.label("b_city"),
            Business.neighborhood.label("b_neighborhood"),
            Business.logo_url.label("b_logo_url"),
            Category.name.label("category_name"),
        )
        .join(Business, Business.id == JobOpening.business_id)
        .outerjoin(
            BusinessCategory,
            (BusinessCategory.business_id == Business.id) & (BusinessCategory.is_primary == True),
        )
        .outerjoin(Category, Category.id == BusinessCategory.category_id)
        .where(
            JobOpening.status == "active",
            JobOpening.owner_paused == False,
            JobOpening.admin_hold == False,
            JobOpening.expires_at > now,
            Business.status == "approved",
        )
        .order_by(JobOpening.published_at.desc().nullslast(), JobOpening.created_at.desc())
        .limit(limit + 1)
        .offset(offset)
    )

    if business_id:
        stmt = stmt.where(JobOpening.business_id == business_id)
    if city:
        stmt = stmt.where(Business.city.ilike(f"%{city}%"))
    if state:
        stmt = stmt.where(Business.state.ilike(f"%{state}%"))
    if contract_type:
        stmt = stmt.where(JobOpening.contract_type == contract_type)
    if category_id:
        stmt = stmt.where(BusinessCategory.category_id == category_id)
    if q:
        search_term = f"%{q.strip()}%"
        stmt = stmt.where(
            or_(
                JobOpening.title.ilike(search_term),
                JobOpening.description.ilike(search_term),
                Business.name.ilike(search_term),
            )
        )

    res = await db.execute(stmt)
    rows = res.all()

    has_more = len(rows) > limit
    returned_rows = rows[:limit]

    items = []
    for row in returned_rows:
        job, b_id, b_name, b_slug, b_city, b_neigh, b_logo, c_name = row
        items.append({
            "id": str(job.id),
            "title": job.title,
            "description": job.description,
            "contract_type": job.contract_type,
            "openings_count": job.openings_count,
            "published_at": job.published_at.isoformat() if job.published_at else None,
            "expires_at": job.expires_at.isoformat() if job.expires_at else None,
            "business": {
                "id": str(b_id),
                "name": b_name,
                "slug": b_slug,
                "city": b_city,
                "neighborhood": b_neigh,
                "logo_url": b_logo,
                "category_name": c_name or "Geral",
            },
        })

    return {
        "page": page,
        "limit": limit,
        "has_more": has_more,
        "total": len(items),
        "results": items,
    }


@router.get("/{job_id}", response_model=Dict[str, Any])
async def get_public_job(
    job_id: UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """
    Retorna detalhes de uma vaga ativa e visível. Retorna 404 se a vaga não for pública.
    """
    now = datetime.now(timezone.utc)
    stmt = (
        select(
            JobOpening,
            Business.id.label("b_id"),
            Business.name.label("b_name"),
            Business.slug.label("b_slug"),
            Business.city.label("b_city"),
            Business.neighborhood.label("b_neighborhood"),
            Business.logo_url.label("b_logo_url"),
            Category.name.label("category_name"),
        )
        .join(Business, Business.id == JobOpening.business_id)
        .outerjoin(
            BusinessCategory,
            (BusinessCategory.business_id == Business.id) & (BusinessCategory.is_primary == True),
        )
        .outerjoin(Category, Category.id == BusinessCategory.category_id)
        .where(
            JobOpening.id == job_id,
            JobOpening.status == "active",
            JobOpening.owner_paused == False,
            JobOpening.admin_hold == False,
            JobOpening.expires_at > now,
            Business.status == "approved",
        )
    )

    res = await db.execute(stmt)
    row = res.first()
    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Vaga de emprego não encontrada ou não mais disponível.",
        )

    job, b_id, b_name, b_slug, b_city, b_neigh, b_logo, c_name = row
    return {
        "id": str(job.id),
        "title": job.title,
        "description": job.description,
        "contract_type": job.contract_type,
        "openings_count": job.openings_count,
        "published_at": job.published_at.isoformat() if job.published_at else None,
        "expires_at": job.expires_at.isoformat() if job.expires_at else None,
        "business": {
            "id": str(b_id),
            "name": b_name,
            "slug": b_slug,
            "city": b_city,
            "neighborhood": b_neigh,
            "logo_url": b_logo,
            "category_name": c_name or "Geral",
        },
    }


@router.post("/{job_id}/report", status_code=status.HTTP_201_CREATED)
async def report_job(
    job_id: UUID,
    payload: JobReportCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """
    Denúncia pública de vaga (Seção 5.4):
    - Rate limit por IP.
    - Deduplicação de denúncia pelo hash do IP nas últimas 24h.
    - Se atingir 3 denúncias distintas nas últimas 24h, aplica admin_hold=True automaticamente na vaga.
    """
    client_ip = get_client_ip(request)
    await check_rate_limit(
        key=f"ratelimit:job_report:{client_ip}",
        limit=5,
        window_seconds=300,
        error_msg="Muitas denúncias enviadas. Por favor aguarde.",
    )

    job_stmt = select(JobOpening).where(JobOpening.id == job_id)
    job = (await db.execute(job_stmt)).scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Vaga de emprego não encontrada.")

    ip_hash = get_ip_hash(client_ip)
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(hours=24)

    # Verifica se este IP já denunciou nas últimas 24h
    existing_rep = (await db.execute(
        select(JobReport.id).where(
            JobReport.job_id == job_id,
            JobReport.ip_hash == ip_hash,
            JobReport.created_at >= cutoff,
        )
    )).scalar_one_or_none()

    if existing_rep:
        # Resposta amigável para evitar abuso ou repetição
        return {"success": True, "message": "Denúncia já registrada anteriormente."}

    new_report = JobReport(
        job_id=job.id,
        reason=payload.reason,
        details=payload.details,
        ip_hash=ip_hash,
    )
    db.add(new_report)
    await db.flush()

    # Conta denúncias distintas nas últimas 24h
    distinct_reports_count = (await db.execute(
        select(func.count(JobReport.id)).where(
            JobReport.job_id == job.id,
            JobReport.created_at >= cutoff,
        )
    )).scalar() or 0

    if distinct_reports_count >= 3 and not job.admin_hold:
        job.admin_hold = True
        log_entry = JobReviewLog(
            job_id=job.id,
            actor="system",
            action="hold",
            from_status=job.status,
            to_status=job.status,
            reason_code="reports_threshold_reached",
            note=f"Bloqueio automático por atingir {distinct_reports_count} denúncias em 24h.",
        )
        db.add(log_entry)
        logger.warning("Vaga %s colocada em admin_hold por limite de 3 denúncias.", job.id)

    await db.commit()
    return {"success": True, "message": "Denúncia recebida e registrada para análise."}
