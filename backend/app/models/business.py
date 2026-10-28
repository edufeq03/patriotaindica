import uuid
from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import ENUM, TSVECTOR, UUID
from sqlalchemy.orm import relationship
from geoalchemy2 import Geography
from backend.app.core.database import Base

listing_type_enum = ENUM("service", "product", "both", name="listing_type", create_type=False)
service_mode_enum = ENUM("at_location", "at_customer", "both", "online", name="service_mode", create_type=False)
business_status_enum = ENUM("draft", "pending_review", "needs_info", "approved", "rejected", "suspended", name="business_status", create_type=False)
business_source_enum = ENUM("seeded", "invited", "application", "claimed", name="business_source", create_type=False)


class Business(Base):
    __tablename__ = "businesses"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    owner_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    name = Column(String(150), nullable=False)
    slug = Column(String(180), unique=True, nullable=False, index=True)
    description = Column(Text, nullable=True)
    listing_type = Column(listing_type_enum, nullable=False, default="service")  # 'service', 'product', 'both'

    # Identificação interna (LGPD) - Permite múltiplos negócios da mesma dona (CPF/CNPJ)
    document_type = Column(String(4), nullable=True)  # 'CNPJ' ou 'CPF'
    document_number = Column(String(14), nullable=True, index=True)
    cnpj_situation = Column(String(50), nullable=True)
    cnpj_checked_at = Column(DateTime(timezone=True), nullable=True)

    # Indicação e Viralidade (Member-Get-Member)
    referral_code = Column(String(50), nullable=True, index=True)
    referred_by_code = Column(String(50), nullable=True)

    # Contatos diretos
    whatsapp = Column(String(20), nullable=False)
    whatsapp_e164 = Column(String(20), nullable=True, index=True)
    whatsapp_verified_at = Column(DateTime(timezone=True), nullable=True)
    phone = Column(String(20), nullable=True)
    website = Column(String(255), nullable=True)
    instagram = Column(String(100), nullable=True)

    # Localização
    street = Column(String(255), nullable=True)
    number = Column(String(50), nullable=True)
    neighborhood = Column(String(100), nullable=False)
    city = Column(String(100), nullable=False)
    state = Column(String(2), nullable=False)
    postal_code = Column(String(10), nullable=True)
    show_full_address = Column(Boolean, nullable=False, default=False)
    location = Column(Geography(geometry_type="POINT", srid=4326), nullable=True)
    geocode_source = Column(String(50), nullable=True)
    geocode_confidence = Column(Float, nullable=True)
    location_pending = Column(Boolean, nullable=False, default=False)
    service_mode = Column(service_mode_enum, nullable=False, default="at_location")  # 'at_location', 'at_customer', 'both', 'online'
    service_radius_km = Column(Integer, nullable=True)
    serves_at_location = Column(Boolean, nullable=False, default=True)
    serves_at_customer = Column(Boolean, nullable=False, default=False)
    serves_online = Column(Boolean, nullable=False, default=False)

    # Mídia
    logo_url = Column(Text, nullable=True)
    banner_url = Column(Text, nullable=True)

    # Curadoria / Triagem
    status = Column(business_status_enum, nullable=False, default="pending_review", index=True)
    owner_paused = Column(Boolean, nullable=False, default=False, index=True)
    document_flag_duplicate = Column(Boolean, nullable=False, default=False)
    source = Column(business_source_enum, nullable=False, default="application")
    is_verified = Column(Boolean, nullable=False, default=False)
    rejection_reason = Column(Text, nullable=True)
    reviewed_by = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    reviewed_at = Column(DateTime(timezone=True), nullable=True)

    # Selos e Reputação da Rede de Negócios Confiáveis
    availability_until = Column(DateTime(timezone=True), nullable=True, index=True)
    network_badge = Column(String(50), nullable=False, default="membro_verificado")
    endorsements_count = Column(Integer, nullable=False, default=0)

    # Full text search
    search_vector = Column(TSVECTOR, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relacionamentos
    categories = relationship("BusinessCategory", back_populates="business", cascade="all, delete-orphan")
    review_logs = relationship("BusinessReviewLog", back_populates="business", cascade="all, delete-orphan")
    contact_events = relationship("ContactEvent", back_populates="business", cascade="all, delete-orphan")
    invitations = relationship("Invitation", back_populates="business", cascade="all, delete-orphan")
    reports = relationship("Report", back_populates="business", cascade="all, delete-orphan")
    endorsements_received = relationship("PeerEndorsement", foreign_keys="PeerEndorsement.endorsed_business_id", cascade="all, delete-orphan")
    endorsements_given = relationship("PeerEndorsement", foreign_keys="PeerEndorsement.endorsing_business_id", cascade="all, delete-orphan")


class PeerEndorsement(Base):
    __tablename__ = "peer_endorsements"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    endorsing_business_id = Column(UUID(as_uuid=True), ForeignKey("businesses.id", ondelete="CASCADE"), nullable=False, index=True)
    endorsed_business_id = Column(UUID(as_uuid=True), ForeignKey("businesses.id", ondelete="CASCADE"), nullable=False, index=True)
    relationship_type = Column(String(30), nullable=False, default="peer")  # 'client', 'partner', 'peer', 'supplier'
    testimonial = Column(String(500), nullable=True)
    is_public = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    endorsing_business = relationship("Business", foreign_keys=[endorsing_business_id], overlaps="endorsements_given")
    endorsed_business = relationship("Business", foreign_keys=[endorsed_business_id], overlaps="endorsements_received")


class BusinessCategory(Base):
    __tablename__ = "business_categories"

    business_id = Column(UUID(as_uuid=True), ForeignKey("businesses.id", ondelete="CASCADE"), primary_key=True)
    category_id = Column(UUID(as_uuid=True), ForeignKey("categories.id", ondelete="RESTRICT"), primary_key=True)
    is_primary = Column(Boolean, nullable=False, default=False)

    business = relationship("Business", back_populates="categories")
    category = relationship("Category", back_populates="businesses")
