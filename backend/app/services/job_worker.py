import logging
from datetime import datetime, timezone
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.jobs import JobOpening, JobReviewLog

logger = logging.getLogger("patriotaindica.jobs.worker")


async def expire_overdue_jobs(db: AsyncSession) -> int:
    """
    Rotina periódica para expirar automaticamente vagas vencidas (Seção 6).
    Transita de 'active' para 'expired' e grava log de auditoria permanente.
    """
    now = datetime.now(timezone.utc)
    stmt = (
        select(JobOpening)
        .where(
            JobOpening.status == "active",
            JobOpening.expires_at <= now,
        )
    )
    result = await db.execute(stmt)
    overdue_jobs = result.scalars().all()

    if not overdue_jobs:
        return 0

    count = 0
    for job in overdue_jobs:
        job.status = "expired"
        log_entry = JobReviewLog(
            job_id=job.id,
            actor="system",
            action="expire",
            from_status="active",
            to_status="expired",
            note="Validade de 30 dias expirada automaticamente pelo sistema.",
        )
        db.add(log_entry)
        count += 1

    await db.commit()
    logger.info("Rotina de vagas: %d vaga(s) expirada(s) automaticamente.", count)
    return count


async def notify_expiring_jobs(db: AsyncSession) -> int:
    """
    Identifica vagas ativas que vão expirar em até 3 dias para alerta preventivo ao lojista (T-V3.4).
    """
    from datetime import timedelta
    from backend.app.models.business import Business

    now = datetime.now(timezone.utc)
    in_three_days = now + timedelta(days=3)

    stmt = (
        select(JobOpening, Business)
        .join(Business, Business.id == JobOpening.business_id)
        .where(
            JobOpening.status == "active",
            JobOpening.owner_paused == False,
            JobOpening.admin_hold == False,
            JobOpening.expires_at > now,
            JobOpening.expires_at <= in_three_days,
            JobOpening.renewed_count < 2,
        )
    )
    result = await db.execute(stmt)
    expiring_pairs = result.all()

    notified = 0
    for job, business in expiring_pairs:
        logger.info(
            "Alerta de expiração de vaga: '%s' da empresa '%s' expira em breve (%s).",
            job.title,
            business.name,
            job.expires_at,
        )
        notified += 1

    return notified


async def get_job_apply_stats(db: AsyncSession, business_id) -> int:
    """
    Retorna o total de cliques de candidatura em vagas para uma empresa (contact_events).
    """
    from sqlalchemy import func
    from backend.app.models.events import ContactEvent

    stmt = select(func.count(ContactEvent.id)).where(
        ContactEvent.business_id == business_id,
        ContactEvent.contact_type == "job_apply",
    )
    total_applies = (await db.execute(stmt)).scalar() or 0
    return total_applies

