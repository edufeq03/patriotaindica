import logging
from typing import Any, Dict, List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.database import get_db
from backend.app.core.security import get_current_active_admin
from backend.app.models.jobs import JobOpening
from backend.app.models.user import User
from backend.app.schemas.jobs import (
    JobAdminOut,
    JobDecisionRequest,
    ModerationTermCreate,
    ModerationTermOut,
)
from backend.app.services.job_service import (
    admin_create_term,
    admin_delete_term,
    admin_get_jobs_queue,
    admin_get_metrics,
    admin_list_terms,
    admin_review_job,
    admin_toggle_term,
)

logger = logging.getLogger("patriotaindica.admin_jobs")
router = APIRouter()


@router.get("/jobs", response_model=List[JobAdminOut])
async def list_admin_jobs(
    status_filter: Optional[str] = Query(None, description="pending_review, active, closed, all"),
    flag: Optional[str] = Query(None, description="hold, paused"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    admin_user: User = Depends(get_current_active_admin),
):
    """
    Fila de moderação de vagas para curadoria (T-V2.1).
    """
    return await admin_get_jobs_queue(
        db=db,
        status_filter=status_filter,
        flag=flag,
        limit=limit,
        offset=offset,
    )


@router.get("/jobs/metrics", response_model=Dict[str, int])
async def get_jobs_metrics(
    db: AsyncSession = Depends(get_db),
    admin_user: User = Depends(get_current_active_admin),
):
    """
    Métricas de vagas para o painel de curadoria.
    """
    return await admin_get_metrics(db)


@router.post("/jobs/{job_id}/decision")
async def apply_job_decision(
    job_id: UUID,
    payload: JobDecisionRequest,
    db: AsyncSession = Depends(get_db),
    admin_user: User = Depends(get_current_active_admin),
):
    """
    Aplica decisão de aprovação, rejeição, bloqueio ou liberação de uma vaga.
    """
    stmt = select(JobOpening).where(JobOpening.id == job_id)
    job = (await db.execute(stmt)).scalar_one_or_none()
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Vaga de emprego não encontrada.",
        )

    updated_job = await admin_review_job(
        job=job,
        admin_user=admin_user,
        action=payload.action,
        reason_code=payload.reason_code,
        note=payload.note,
        db=db,
    )

    return {
        "success": True,
        "job_id": updated_job.id,
        "status": updated_job.status,
        "admin_hold": updated_job.admin_hold,
        "action": payload.action,
    }


@router.get("/moderation-terms", response_model=List[ModerationTermOut])
async def list_moderation_terms(
    category: Optional[str] = Query(None),
    active: Optional[bool] = Query(None),
    db: AsyncSession = Depends(get_db),
    admin_user: User = Depends(get_current_active_admin),
):
    """
    Lista termos monitorados pela moderação automática.
    """
    return await admin_list_terms(db=db, category=category, active=active)


@router.post("/moderation-terms", response_model=ModerationTermOut, status_code=status.HTTP_201_CREATED)
async def create_moderation_term(
    payload: ModerationTermCreate,
    db: AsyncSession = Depends(get_db),
    admin_user: User = Depends(get_current_active_admin),
):
    """
    Adiciona novo termo à tabela de moderação automática.
    """
    return await admin_create_term(
        term=payload.term,
        category=payload.category,
        severity=payload.severity,
        match_type=payload.match_type,
        db=db,
    )


@router.patch("/moderation-terms/{term_id}")
async def toggle_moderation_term(
    term_id: UUID,
    active: bool = Query(...),
    db: AsyncSession = Depends(get_db),
    admin_user: User = Depends(get_current_active_admin),
):
    """
    Ativa ou desativa um termo de moderação.
    """
    term = await admin_toggle_term(term_id=term_id, active=active, db=db)
    return {"success": True, "id": term.id, "active": term.active}


@router.delete("/moderation-terms/{term_id}")
async def delete_moderation_term(
    term_id: UUID,
    db: AsyncSession = Depends(get_db),
    admin_user: User = Depends(get_current_active_admin),
):
    """
    Remove um termo de moderação.
    """
    return await admin_delete_term(term_id=term_id, db=db)
