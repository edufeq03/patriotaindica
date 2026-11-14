import uuid
from datetime import datetime, timezone
from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    SmallInteger,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from backend.app.core.database import Base


class JobOpening(Base):
    __tablename__ = "job_openings"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    business_id = Column(UUID(as_uuid=True), ForeignKey("businesses.id", ondelete="CASCADE"), nullable=False, index=True)
    title = Column(String(60), nullable=False)
    title_normalized = Column(String(60), nullable=False, index=True)
    description = Column(String(280), nullable=True)
    contract_type = Column(String(30), nullable=False)  # 'clt', 'temporario', 'meio_periodo', 'estagio', 'aprendiz', 'autonomo'
    openings_count = Column(SmallInteger, nullable=False, default=1)
    status = Column(String(20), nullable=False, default="pending_review", index=True)  # 'pending_review', 'active', 'expired', 'closed', 'rejected'
    owner_paused = Column(Boolean, nullable=False, default=False)
    admin_hold = Column(Boolean, nullable=False, default=False)
    moderation_flags = Column(JSONB, nullable=False, default=list)
    rejection_code = Column(String(40), nullable=True)
    published_at = Column(DateTime(timezone=True), nullable=True)
    expires_at = Column(DateTime(timezone=True), nullable=True, index=True)
    renewed_count = Column(SmallInteger, nullable=False, default=0)
    close_reason = Column(String(30), nullable=True)  # 'hired_here', 'hired_other', 'gave_up', 'other'
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    business = relationship("Business", backref="job_openings")
    creator = relationship("User", foreign_keys=[created_by])
    review_logs = relationship("JobReviewLog", back_populates="job", cascade="all, delete-orphan")
    reports = relationship("JobReport", back_populates="job", cascade="all, delete-orphan")

    @property
    def is_publicly_visible(self) -> bool:
        """Regra de visibilidade pública conforme Seção 4 da especificação."""
        if self.status != "active" or self.owner_paused or self.admin_hold:
            return False
        now = datetime.now(timezone.utc)
        if self.expires_at and self.expires_at <= now:
            return False
        if self.business and (self.business.status != "approved" or getattr(self.business, "owner_paused", False)):
            return False
        return True


class JobReviewLog(Base):
    __tablename__ = "job_review_log"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    job_id = Column(UUID(as_uuid=True), ForeignKey("job_openings.id", ondelete="RESTRICT"), nullable=False, index=True)
    actor = Column(String(10), nullable=False)  # 'system', 'admin', 'owner'
    actor_id = Column(UUID(as_uuid=True), nullable=True)
    action = Column(String(30), nullable=False)  # 'auto_publish', 'flag_review', 'approve', 'reject', 'hold', 'release', 'expire', 'close', 'renew'
    from_status = Column(String(20), nullable=True)
    to_status = Column(String(20), nullable=True)
    reason_code = Column(String(40), nullable=True)
    flags = Column(JSONB, nullable=True)
    note = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    job = relationship("JobOpening", back_populates="review_logs")


class JobReport(Base):
    __tablename__ = "job_reports"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    job_id = Column(UUID(as_uuid=True), ForeignKey("job_openings.id", ondelete="CASCADE"), nullable=False, index=True)
    reason = Column(String(20), nullable=False)  # 'golpe', 'discriminacao', 'improprio', 'outro'
    details = Column(String(200), nullable=True)
    ip_hash = Column(String(64), nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    job = relationship("JobOpening", back_populates="reports")


class ModerationTerm(Base):
    __tablename__ = "moderation_terms"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    term_normalized = Column(String(80), unique=True, nullable=False, index=True)
    category = Column(String(20), nullable=False)  # 'discriminacao', 'conviccao', 'golpe', 'improprio', 'review'
    severity = Column(String(10), nullable=False)  # 'block', 'review'
    match_type = Column(String(10), nullable=False, default="phrase")  # 'word', 'phrase'
    active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
