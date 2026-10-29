from typing import List
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.database import get_db
from backend.app.core.rate_limit import check_rate_limit, get_client_ip
from backend.app.core.security import get_current_user
from backend.app.models.business import Business
from backend.app.models.jobs import JobOpening
from backend.app.models.user import User
from backend.app.schemas.jobs import JobClose, JobCreate, JobOut, JobUpdate
from backend.app.services.job_service import (
    close_job_opening,
    create_job_opening,
    renew_job_opening,
    toggle_job_pause,
    update_job_opening,
)

router = APIRouter()


async def get_owned_business(
    business_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Business:
    """
    SEGURANÇA (Seção 7 e 11): Dependency contra IDOR.
    Garante que o recurso pertence estritamente ao usuário autenticado ou admin.
    """
    stmt = select(Business).where(Business.id == business_id)
    res = await db.execute(stmt)
    business = res.scalar_one_or_none()
    if not business:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Empresa não encontrada.")

    if current_user.role != "admin" and business.owner_user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Empresa não encontrada ou sem permissão.")

    return business


async def get_owned_job(
    job_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> JobOpening:
    """
    SEGURANÇA (Seção 7 e 11): Dependency contra IDOR para vagas.
    """
    stmt = select(JobOpening).where(JobOpening.id == job_id)
    res = await db.execute(stmt)
    job = res.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vaga não encontrada.")

    # Verifica a posse da empresa correspondente
    biz_stmt = select(Business.owner_user_id).where(Business.id == job.business_id)
    owner_id = (await db.execute(biz_stmt)).scalar_one_or_none()

    if current_user.role != "admin" and owner_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vaga não encontrada ou sem permissão.")

    return job


@router.get("/businesses/{business_id}/jobs", response_model=List[JobOut])
async def list_business_jobs(
    business: Business = Depends(get_owned_business),
    db: AsyncSession = Depends(get_db),
):
    """
    Lista todas as vagas cadastradas para a empresa gerenciada.
    """
    stmt = (
        select(JobOpening)
        .where(JobOpening.business_id == business.id)
        .order_by(JobOpening.created_at.desc())
    )
    result = await db.execute(stmt)
    jobs = result.scalars().all()
    return jobs


@router.post("/businesses/{business_id}/jobs", response_model=JobOut, status_code=status.HTTP_201_CREATED)
async def create_business_job(
    payload: JobCreate,
    request: Request,
    business: Business = Depends(get_owned_business),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Cadastra uma nova vaga aberta para a empresa.
    Rate limit: máximo 5 criações por dia por empresa; 20 por dia por IP.
    """
    client_ip = get_client_ip(request)
    await check_rate_limit(
        key=f"ratelimit:jobs:create:ip:{client_ip}",
        limit=20,
        window_seconds=86400,
        error_msg="Limite diário de criação de vagas por endereço IP atingido.",
    )
    await check_rate_limit(
        key=f"ratelimit:jobs:create:biz:{business.id}",
        limit=5,
        window_seconds=86400,
        error_msg="Limite de 5 criações de vagas por dia atingido para esta empresa.",
    )

    job = await create_job_opening(
        business=business,
        user=current_user,
        payload=payload,
        db=db,
    )
    return job


@router.put("/jobs/{job_id}", response_model=JobOut)
async def update_job(
    payload: JobUpdate,
    request: Request,
    job: JobOpening = Depends(get_owned_job),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Atualiza título, descrição ou dados da vaga com reexecução da moderação.
    Rate limit: máximo 10 edições por dia por vaga.
    """
    await check_rate_limit(
        key=f"ratelimit:jobs:update:{job.id}",
        limit=10,
        window_seconds=86400,
        error_msg="Limite diário de edições para esta vaga atingido.",
    )

    updated_job = await update_job_opening(
        job=job,
        user=current_user,
        payload=payload,
        db=db,
    )
    return updated_job


@router.post("/jobs/{job_id}/pause", response_model=JobOut)
async def pause_job(
    job: JobOpening = Depends(get_owned_job),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Pausa temporariamente a exibição pública da vaga.
    """
    return await toggle_job_pause(job=job, user=current_user, pause=True, db=db)


@router.post("/jobs/{job_id}/resume", response_model=JobOut)
async def resume_job(
    job: JobOpening = Depends(get_owned_job),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Reativa a exibição pública da vaga pausada pelo dono.
    """
    return await toggle_job_pause(job=job, user=current_user, pause=False, db=db)


@router.post("/jobs/{job_id}/close", response_model=JobOut)
async def close_job(
    payload: JobClose,
    job: JobOpening = Depends(get_owned_job),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Encerra a vaga definitivamente informando o motivo.
    """
    return await close_job_opening(
        job=job,
        user=current_user,
        close_reason=payload.close_reason,
        db=db,
    )


@router.post("/jobs/{job_id}/renew", response_model=JobOut)
async def renew_job(
    job: JobOpening = Depends(get_owned_job),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Renova a vaga por mais 30 dias (máximo 2 renovações).
    """
    return await renew_job_opening(job=job, user=current_user, db=db)
