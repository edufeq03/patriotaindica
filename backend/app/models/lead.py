import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from geoalchemy2 import Geography

from backend.app.core.database import Base


class Lead(Base):
    __tablename__ = "leads"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    client_phone_e164 = Column(String(30), nullable=False)
    client_name = Column(String(100), nullable=True)
    category_id = Column(UUID(as_uuid=True), ForeignKey("categories.id", ondelete="SET NULL"), nullable=True, index=True)
    description = Column(Text, nullable=False)
    urgency = Column(String(30), nullable=False, default="normal")  # 'urgent', 'normal', 'budget'
    location = Column(Geography(geometry_type="POINT", srid=4326), nullable=True)
    city = Column(String(100), nullable=True)
    state = Column(String(2), nullable=True)
    status = Column(String(30), nullable=False, default="pending_offers", index=True)  # 'pending_offers', 'matched', 'expired', 'canceled'
    matched_business_id = Column(UUID(as_uuid=True), ForeignKey("businesses.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), index=True)
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    category = relationship("Category")
    matched_business = relationship("Business", foreign_keys=[matched_business_id])
    offers = relationship("LeadOffer", back_populates="lead", cascade="all, delete-orphan")


class LeadOffer(Base):
    __tablename__ = "lead_offers"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    lead_id = Column(UUID(as_uuid=True), ForeignKey("leads.id", ondelete="CASCADE"), nullable=False, index=True)
    business_id = Column(UUID(as_uuid=True), ForeignKey("businesses.id", ondelete="CASCADE"), nullable=False, index=True)
    offer_code = Column(String(20), nullable=False, index=True)
    status = Column(String(30), nullable=False, default="sent")  # 'sent', 'accepted', 'declined', 'expired'
    sent_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    responded_at = Column(DateTime(timezone=True), nullable=True)
    response_seconds = Column(Integer, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    lead = relationship("Lead", back_populates="offers")
    business = relationship("Business")


class LeadReview(Base):
    __tablename__ = "lead_reviews"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    lead_id = Column(UUID(as_uuid=True), ForeignKey("leads.id", ondelete="CASCADE"), nullable=False)
    business_id = Column(UUID(as_uuid=True), ForeignKey("businesses.id", ondelete="CASCADE"), nullable=False, index=True)
    rating = Column(Integer, nullable=False)  # 1 a 5
    comment = Column(Text, nullable=True)
    status = Column(String(30), nullable=False, default="approved")  # 'pending_moderation', 'approved', 'rejected'
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    lead = relationship("Lead")
    business = relationship("Business")
