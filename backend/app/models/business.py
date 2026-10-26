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
from sqlalchemy.dialects.postgresql import TSVECTOR, UUID
from sqlalchemy.orm import relationship
from geoalchemy2 import Geography
from backend.app.core.database import Base


class Business(Base):
    __tablename__ = "businesses"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    owner_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    name = Column(String(150), nullable=False)
    slug = Column(String(180), unique=True, nullable=False, index=True)
    description = Column(Text, nullable=True)
    listing_type = Column(String(20), nullable=False, default="service")  # 'service', 'product', 'both'

    # Identificação interna (LGPD)
    document_type = Column(String(4), nullable=True)  # 'CNPJ' ou 'CPF'
    document_number = Column(String(14), unique=True, nullable=True)
    cnpj_situation = Column(String(50), nullable=True)
    cnpj_checked_at = Column(DateTime(timezone=True), nullable=True)

    # Contatos diretos
    whatsapp = Column(String(20), nullable=False)
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
    service_mode = Column(String(20), nullable=False, default="at_location")  # 'at_location', 'at_customer', 'both', 'online'
    service_radius_km = Column(Integer, nullable=True)

    # Mídia
    logo_url = Column(Text, nullable=True)
    banner_url = Column(Text, nullable=True)

    # Curadoria / Triagem
    status = Column(String(20), nullable=False, default="pending_review", index=True)
    source = Column(String(20), nullable=False, default="application")
    is_verified = Column(Boolean, nullable=False, default=False)
    rejection_reason = Column(Text, nullable=True)
    reviewed_by = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    reviewed_at = Column(DateTime(timezone=True), nullable=True)

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


class BusinessCategory(Base):
    __tablename__ = "business_categories"

    business_id = Column(UUID(as_uuid=True), ForeignKey("businesses.id", ondelete="CASCADE"), primary_key=True)
    category_id = Column(UUID(as_uuid=True), ForeignKey("categories.id", ondelete="RESTRICT"), primary_key=True)
    is_primary = Column(Boolean, nullable=False, default=False)

    business = relationship("Business", back_populates="categories")
    category = relationship("Category", back_populates="businesses")
