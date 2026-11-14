import uuid
from datetime import datetime, timezone
from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from backend.app.core.database import Base


class Plan(Base):
    __tablename__ = "plans"

    id = Column(String(30), primary_key=True)  # 'mensal', 'semestral', 'anual'
    name = Column(String(50), nullable=False)
    price_cents = Column(Integer, nullable=False)
    monthly_equivalent_cents = Column(Integer, nullable=False)
    duration_months = Column(Integer, nullable=False)
    description = Column(Text, nullable=True)
    badge = Column(String(100), nullable=True)
    is_featured = Column(Boolean, nullable=False, default=False)
    search_priority = Column(Integer, nullable=False, default=1)
    max_categories = Column(Integer, nullable=False, default=1)
    max_photos = Column(Integer, nullable=False, default=3)
    has_leads_access = Column(Boolean, nullable=False, default=False)
    has_metrics_access = Column(Boolean, nullable=False, default=False)
    has_banner_access = Column(Boolean, nullable=False, default=False)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))



class Subscription(Base):
    __tablename__ = "subscriptions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    owner_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True)
    business_id = Column(UUID(as_uuid=True), ForeignKey("businesses.id", ondelete="SET NULL"), nullable=True)
    plan_id = Column(String(30), ForeignKey("plans.id"), nullable=False)
    status = Column(String(30), nullable=False, default="active", index=True)  # 'active', 'past_due', 'canceled'
    current_period_start = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    current_period_end = Column(DateTime(timezone=True), nullable=False)
    mp_payment_id = Column(String(100), nullable=True)
    mp_preference_id = Column(String(100), nullable=True)
    bonus_months_applied = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    owner = relationship("User", foreign_keys=[owner_user_id])
    plan = relationship("Plan")
    business = relationship("Business", foreign_keys=[business_id])


class Referral(Base):
    __tablename__ = "referrals"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    referrer_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    referrer_business_id = Column(UUID(as_uuid=True), ForeignKey("businesses.id", ondelete="SET NULL"), nullable=True)
    referred_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    referred_business_id = Column(UUID(as_uuid=True), ForeignKey("businesses.id", ondelete="CASCADE"), nullable=False)
    code = Column(String(50), nullable=False, index=True)
    status = Column(String(30), nullable=False, default="pending")  # 'pending', 'rewarded'
    reward_granted_days = Column(Integer, nullable=False, default=30)
    rewarded_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
