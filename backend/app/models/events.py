import uuid
from sqlalchemy import BigInteger, Column, DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import ENUM, JSONB, UUID
from sqlalchemy.orm import relationship
from backend.app.core.database import Base

business_status_enum = ENUM("draft", "pending_review", "needs_info", "approved", "rejected", "suspended", name="business_status", create_type=False)


class BusinessReviewLog(Base):
    __tablename__ = "business_review_log"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    business_id = Column(UUID(as_uuid=True), ForeignKey("businesses.id", ondelete="CASCADE"), nullable=False, index=True)
    from_status = Column(business_status_enum, nullable=True)
    to_status = Column(business_status_enum, nullable=False)
    note = Column(Text, nullable=True)
    admin_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    business = relationship("Business", back_populates="review_logs")


class BusinessPendingChange(Base):
    """
    SEGURANÇA (H3): Modificações propostas pelo proprietário da empresa.
    Campos de risco (website, instagram, telefone, categorias, etc.)
    ficam em quarentena até aprovação da curadoria, mantendo a versão aprovada no ar.
    """
    __tablename__ = "business_pending_changes"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    business_id = Column(UUID(as_uuid=True), ForeignKey("businesses.id", ondelete="CASCADE"), nullable=False, index=True)
    proposed_by_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    changes = Column(JSONB, nullable=False)
    status = Column(String(20), nullable=False, default="pending_review", index=True)  # 'pending_review', 'approved', 'rejected'
    reviewed_by = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    reviewed_at = Column(DateTime(timezone=True), nullable=True)
    rejection_reason = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    business = relationship("Business")
    proposed_by = relationship("User", foreign_keys=[proposed_by_user_id])
    reviewer = relationship("User", foreign_keys=[reviewed_by])


class Invitation(Base):
    """
    SEGURANÇA (M12): Convites vinculados a tokens criptográficos.
    Armazena apenas o HASH SHA-256 do token gerado com secrets.token_urlsafe(32).
    """
    __tablename__ = "invitations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    token_hash = Column(String(64), unique=True, nullable=False, index=True)
    business_id = Column(UUID(as_uuid=True), ForeignKey("businesses.id", ondelete="CASCADE"), nullable=False)
    phone = Column(String(20), nullable=True)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    used_at = Column(DateTime(timezone=True), nullable=True)
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    business = relationship("Business", back_populates="invitations")


class ContactEvent(Base):
    __tablename__ = "contact_events"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    business_id = Column(UUID(as_uuid=True), ForeignKey("businesses.id", ondelete="CASCADE"), nullable=False, index=True)
    event_type = Column(String(20), nullable=False, index=True)  # 'whatsapp', 'phone', 'website', 'profile_view'
    city = Column(String(100), nullable=True)
    referrer = Column(Text, nullable=True)
    user_agent = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    business = relationship("Business", back_populates="contact_events")


class Report(Base):
    __tablename__ = "reports"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    business_id = Column(UUID(as_uuid=True), ForeignKey("businesses.id", ondelete="CASCADE"), nullable=False, index=True)
    reason = Column(String(100), nullable=False)
    details = Column(Text, nullable=True)
    contact_email = Column(String(255), nullable=True)
    status = Column(String(20), nullable=False, default="pending", index=True)
    resolved_at = Column(DateTime(timezone=True), nullable=True)
    resolved_by = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    business = relationship("Business", back_populates="reports")


class DataSubjectRequest(Base):
    """
    CONFORMIDADE LGPD (M11): Registro auditavel de solicitacoes dos titulares de dados
    (exclusao, revogacao de consentimento, portabilidade, retificacao).
    """
    __tablename__ = "data_subject_requests"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    request_type = Column(String(32), nullable=False)
    email = Column(String(255), nullable=False, index=True)
    phone = Column(String(32), nullable=True)
    details = Column(Text, nullable=True)
    status = Column(String(32), nullable=False, default="received", index=True)
    ip_hash = Column(String(64), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    resolved_at = Column(DateTime(timezone=True), nullable=True)


class Consent(Base):
    """
    CONFORMIDADE LGPD (T1.6): Registro auditável de consentimentos (Carta de Princípios, Termos e Privacidade).
    """
    __tablename__ = "consents"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    business_id = Column(UUID(as_uuid=True), ForeignKey("businesses.id", ondelete="CASCADE"), nullable=True, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    type = Column(String(50), nullable=False, index=True)  # 'carta_principios', 'terms_of_service', 'privacy_policy'
    version = Column(String(20), nullable=False, default="1.0")
    accepted_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    ip_hash = Column(String(64), nullable=True)
    user_agent_hash = Column(String(64), nullable=True)
    revoked_at = Column(DateTime(timezone=True), nullable=True)
