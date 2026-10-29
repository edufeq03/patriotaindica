import uuid
from datetime import datetime, timedelta, timezone
from typing import List, Optional
from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.config import settings
from backend.app.models.business import Business
from backend.app.models.jobs import JobOpening, JobReviewLog, ModerationTerm
from backend.app.models.user import User
from backend.app.schemas.jobs import JobCreate, JobUpdate
from backend.app.services.job_moderation import (
    check_job_content,
    normalize_for_moderation,
)


async def get_active_moderation_rules(db: AsyncSession):
    try:
        stmt = select(
            ModerationTerm.term_normalized,
            ModerationTerm.category,
            ModerationTerm.severity,
            ModerationTerm.match_type,
        ).where(ModerationTerm.active == True)
        res = await db.execute(stmt)
        rules = res.all()
        if rules:
            return [(r[0], r[1], r[2], r[3]) for r in rules]
    except Exception:
        pass
    return None


async def create_job_opening(
    business: Business,
    user: User,
    payload: JobCreate,
    db: AsyncSession,
) -> JobOpening:
    """
    Criação de vaga pelo proprietário (Seção 5 e 7).
    """
    # 1. Regra de negócio: Apenas empresas aprovadas podem divulgar vagas
    if business.status != "approved":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Apenas empresas aprovadas na curadoria do Patriota Indica podem publicar vagas.",
        )

    # 2. Limite estrito de 3 vagas ativas ou em análise por empresa
    count_stmt = select(func.count(JobOpening.id)).where(
        JobOpening.business_id == business.id,
        JobOpening.status.in_(["pending_review", "active"]),
    )
    current_count = (await db.execute(count_stmt)).scalar() or 0
    if current_count >= 3:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Limite de 3 vagas ativas por empresa atingido. Encerre ou aguarde uma vaga anterior expirar.",
        )

    # 3. Unicidade de título normalizado na mesma empresa
    title_norm = normalize_for_moderation(payload.title)
    dup_stmt = select(JobOpening.id).where(
        JobOpening.business_id == business.id,
        JobOpening.title_normalized == title_norm,
        JobOpening.status.in_(["pending_review", "active"]),
    )
    existing_dup = (await db.execute(dup_stmt)).scalar_one_or_none()
    if existing_dup:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Já existe uma vaga aberta ou em análise com este mesmo cargo/título nesta empresa.",
        )

    # 4. Moderação automática de conteúdo
    db_rules = await get_active_moderation_rules(db)
    mod_result = check_job_content(
        title=payload.title,
        description=payload.description,
        contract_type=payload.contract_type,
        custom_rules=db_rules,
    )

    if mod_result.is_blocked:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=mod_result.educational_message,
        )

    # 5. Definição de status e ciclo de vida
    now = datetime.now(timezone.utc)
    auto_publish = getattr(settings, "JOBS_AUTO_PUBLISH", True)

    if mod_result.is_review or not auto_publish:
        initial_status = "pending_review"
        pub_at = None
        exp_at = None
        action_name = "flag_review"
    else:
        initial_status = "active"
        pub_at = now
        exp_at = now + timedelta(days=30)
        action_name = "auto_publish"

    new_job = JobOpening(
        business_id=business.id,
        title=payload.title,
        title_normalized=title_norm,
        description=payload.description,
        contract_type=payload.contract_type,
        openings_count=payload.openings_count,
        status=initial_status,
        owner_paused=False,
        admin_hold=False,
        moderation_flags=mod_result.flags,
        published_at=pub_at,
        expires_at=exp_at,
        renewed_count=0,
        created_by=user.id,
    )

    db.add(new_job)
    await db.flush()

    # Log de Auditoria
    log_entry = JobReviewLog(
        job_id=new_job.id,
        actor="owner" if initial_status == "pending_review" else "system",
        actor_id=user.id,
        action=action_name,
        from_status=None,
        to_status=initial_status,
        flags=mod_result.flags,
        note="Vaga criada pelo proprietário da empresa."
        + (" Publicada automaticamente." if initial_status == "active" else " Enviada para fila de curadoria."),
    )
    db.add(log_entry)
    await db.commit()
    await db.refresh(new_job)

    return new_job


async def update_job_opening(
    job: JobOpening,
    user: User,
    payload: JobUpdate,
    db: AsyncSession,
) -> JobOpening:
    """
    Edição de vaga pelo proprietário (reexecuta moderação).
    """
    new_title = payload.title if payload.title is not None else job.title
    new_desc = payload.description if payload.description is not None else job.description
    new_type = payload.contract_type if payload.contract_type is not None else job.contract_type

    # Reexecuta moderação se houve alteração de texto ou tipo de contrato
    db_rules = await get_active_moderation_rules(db)
    mod_result = check_job_content(
        title=new_title,
        description=new_desc,
        contract_type=new_type,
        custom_rules=db_rules,
    )

    if mod_result.is_blocked:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=mod_result.educational_message,
        )

    job.title = new_title
    job.title_normalized = normalize_for_moderation(new_title)
    job.description = new_desc
    job.contract_type = new_type
    if payload.openings_count is not None:
        job.openings_count = payload.openings_count

    if mod_result.is_review and job.status == "active":
        # Se foi editada com termos suspeitos, volta para análise
        job.status = "pending_review"
        job.moderation_flags = mod_result.flags

        log_entry = JobReviewLog(
            job_id=job.id,
            actor="owner",
            actor_id=user.id,
            action="flag_review",
            from_status="active",
            to_status="pending_review",
            flags=mod_result.flags,
            note="Vaga editada com termos ambíguos; enviada para moderação administrativa.",
        )
        db.add(log_entry)

    await db.commit()
    await db.refresh(job)
    return job


async def toggle_job_pause(
    job: JobOpening,
    user: User,
    pause: bool,
    db: AsyncSession,
) -> JobOpening:
    """
    Pausa ou reativação pelo dono.
    """
    if not pause and job.admin_hold:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Esta vaga possui bloqueio administrativo permanente ou por denúncias e não pode ser reativada pelo proprietário.",
        )

    job.owner_paused = pause
    log_entry = JobReviewLog(
        job_id=job.id,
        actor="owner",
        actor_id=user.id,
        action="pause" if pause else "resume",
        from_status=job.status,
        to_status=job.status,
        note=f"Proprietário {'pausou' if pause else 'reativou'} a exibição da vaga.",
    )
    db.add(log_entry)
    await db.commit()
    await db.refresh(job)
    return job


async def close_job_opening(
    job: JobOpening,
    user: User,
    close_reason: str,
    db: AsyncSession,
) -> JobOpening:
    """
    Encerramento da vaga pelo dono.
    """
    job.status = "closed"
    job.close_reason = close_reason

    log_entry = JobReviewLog(
        job_id=job.id,
        actor="owner",
        actor_id=user.id,
        action="close",
        from_status=job.status,
        to_status="closed",
        reason_code=close_reason,
        note=f"Vaga encerrada pelo proprietário (Motivo: {close_reason}).",
    )
    db.add(log_entry)
    await db.commit()
    await db.refresh(job)
    return job


async def renew_job_opening(
    job: JobOpening,
    user: User,
    db: AsyncSession,
) -> JobOpening:
    """
    Renovação da vaga por mais 30 dias (máximo 2 renovações).
    """
    if job.admin_hold:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Vagas sob moderação administrativa não podem ser renovadas.",
        )

    if job.renewed_count >= 2:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Esta vaga já atingiu o limite máximo de 2 renovações permitidas. Crie um novo anúncio se necessário.",
        )

    # Reexecuta moderação
    db_rules = await get_active_moderation_rules(db)
    mod_result = check_job_content(
        title=job.title,
        description=job.description,
        contract_type=job.contract_type,
        custom_rules=db_rules,
    )
    if mod_result.is_blocked:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=mod_result.educational_message,
        )

    now = datetime.now(timezone.utc)
    job.renewed_count += 1
    job.expires_at = now + timedelta(days=30)
    job.status = "active"
    job.owner_paused = False

    log_entry = JobReviewLog(
        job_id=job.id,
        actor="owner",
        actor_id=user.id,
        action="renew",
        from_status=job.status,
        to_status="active",
        note=f"Vaga renovada com sucesso por mais 30 dias (Renovação {job.renewed_count}/2).",
    )
    db.add(log_entry)
    await db.commit()
    await db.refresh(job)
    return job
