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
