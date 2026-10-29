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


async def admin_review_job(
    job: JobOpening,
    admin_user: User,
    action: str,
    reason_code: Optional[str],
    note: Optional[str],
    db: AsyncSession,
) -> JobOpening:
    """
    Decisão de moderação pelo administrador (T-V2.1):
    action in ('approve', 'reject', 'hold', 'release')
    """
    old_status = job.status
    now = datetime.now(timezone.utc)

    if action == "approve":
        job.status = "active"
        job.admin_hold = False
        job.owner_paused = False
        job.rejection_code = None
        if not job.published_at:
            job.published_at = now
        job.expires_at = now + timedelta(days=30)
    elif action == "reject":
        job.status = "rejected"
        job.admin_hold = False
        job.rejection_code = reason_code or "conteudo_inadequado"
    elif action == "hold":
        job.admin_hold = True
    elif action == "release":
        job.admin_hold = False
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Ação de moderação '{action}' inválida.",
        )

    log_entry = JobReviewLog(
        job_id=job.id,
        actor="admin",
        actor_id=admin_user.id,
        action=action,
        from_status=old_status,
        to_status=job.status,
        reason_code=reason_code,
        note=note or f"Decisão administrativa '{action}' aplicada pelo curador.",
    )
    db.add(log_entry)
    await db.commit()
    await db.refresh(job)
    return job


async def admin_get_jobs_queue(
    db: AsyncSession,
    status_filter: Optional[str] = None,
    flag: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
):
    """
    Retorna fila de vagas para curadoria administrativa com dados da empresa e contagem de denúncias.
    """
    from backend.app.models.jobs import JobReport

    stmt = (
        select(
            JobOpening,
            Business.name.label("business_name"),
            Business.city.label("business_city"),
            Business.state.label("business_state"),
            Business.cnpj.label("business_cnpj"),
            func.count(JobReport.id).label("reports_count"),
        )
        .join(Business, Business.id == JobOpening.business_id)
        .outerjoin(JobReport, JobReport.job_id == JobOpening.id)
        .group_by(JobOpening.id, Business.id)
        .order_by(JobOpening.created_at.desc())
        .limit(limit)
        .offset(offset)
    )

    if status_filter and status_filter != "all":
        stmt = stmt.where(JobOpening.status == status_filter)
    if flag == "hold":
        stmt = stmt.where(JobOpening.admin_hold == True)
    elif flag == "paused":
        stmt = stmt.where(JobOpening.owner_paused == True)

    results = (await db.execute(stmt)).all()
    out = []
    for row in results:
        job, b_name, b_city, b_state, b_cnpj, rep_count = row
        out.append({
            "id": job.id,
            "business_id": job.business_id,
            "business_name": b_name,
            "business_city": b_city,
            "business_state": b_state,
            "business_cnpj": b_cnpj,
            "title": job.title,
            "description": job.description,
            "contract_type": job.contract_type,
            "openings_count": job.openings_count,
            "status": job.status,
            "owner_paused": job.owner_paused,
            "admin_hold": job.admin_hold,
            "moderation_flags": job.moderation_flags or [],
            "rejection_code": job.rejection_code,
            "published_at": job.published_at,
            "expires_at": job.expires_at,
            "renewed_count": job.renewed_count,
            "close_reason": job.close_reason,
            "reports_count": rep_count or 0,
            "created_at": job.created_at,
            "updated_at": job.updated_at,
        })
    return out


async def admin_get_metrics(db: AsyncSession):
    """
    Métricas de vagas para o painel de curadoria.
    """
    total_active = (await db.execute(
        select(func.count(JobOpening.id)).where(JobOpening.status == "active")
    )).scalar() or 0

    total_pending = (await db.execute(
        select(func.count(JobOpening.id)).where(JobOpening.status == "pending_review")
    )).scalar() or 0

    total_hold = (await db.execute(
        select(func.count(JobOpening.id)).where(JobOpening.admin_hold == True)
    )).scalar() or 0

    total_closed = (await db.execute(
        select(func.count(JobOpening.id)).where(JobOpening.status == "closed")
    )).scalar() or 0

    return {
        "active": total_active,
        "pending_review": total_pending,
        "admin_hold": total_hold,
        "closed": total_closed,
        "total": total_active + total_pending + total_closed,
    }


async def admin_list_terms(
    db: AsyncSession,
    category: Optional[str] = None,
    active: Optional[bool] = None,
):
    stmt = select(ModerationTerm).order_by(ModerationTerm.created_at.desc())
    if category:
        stmt = stmt.where(ModerationTerm.category == category)
    if active is not None:
        stmt = stmt.where(ModerationTerm.active == active)
    res = await db.execute(stmt)
    return res.scalars().all()


async def admin_create_term(
    term: str,
    category: str,
    severity: str,
    match_type: str,
    db: AsyncSession,
):
    norm = normalize_for_moderation(term)
    existing = (await db.execute(
        select(ModerationTerm).where(ModerationTerm.term_normalized == norm)
    )).scalar_one_or_none()

    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"O termo '{norm}' já existe na lista de moderação.",
        )

    new_term = ModerationTerm(
        term_normalized=norm,
        category=category,
        severity=severity,
        match_type=match_type,
        active=True,
    )
    db.add(new_term)
    await db.commit()
    await db.refresh(new_term)
    return new_term


async def admin_toggle_term(term_id: uuid.UUID, active: bool, db: AsyncSession):
    term = (await db.execute(
        select(ModerationTerm).where(ModerationTerm.id == term_id)
    )).scalar_one_or_none()
    if not term:
        raise HTTPException(status_code=404, detail="Termo de moderação não encontrado.")
    term.active = active
    await db.commit()
    await db.refresh(term)
    return term


async def admin_delete_term(term_id: uuid.UUID, db: AsyncSession):
    term = (await db.execute(
        select(ModerationTerm).where(ModerationTerm.id == term_id)
    )).scalar_one_or_none()
    if not term:
        raise HTTPException(status_code=404, detail="Termo de moderação não encontrado.")
    await db.delete(term)
    await db.commit()
    return {"success": True}

