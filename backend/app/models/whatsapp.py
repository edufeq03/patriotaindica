import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, DateTime, String
from sqlalchemy.dialects.postgresql import JSONB, UUID

from backend.app.core.database import Base


class WaEvent(Base):
    __tablename__ = "wa_events"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    provider = Column(String(30), nullable=False)  # 'meta_cloud', 'evolution'
    event_id = Column(String(150), unique=True, nullable=False, index=True)
    payload = Column(JSONB, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


class WaOptin(Base):
    __tablename__ = "wa_optins"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    phone_e164 = Column(String(30), nullable=False, index=True)
    scope = Column(String(50), nullable=False, default="all")  # 'auth', 'utility', 'marketing', 'all'
    status = Column(String(20), nullable=False, default="active", index=True)  # 'active', 'revoked'
    origin = Column(String(50), nullable=False, default="whatsapp")
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    revoked_at = Column(DateTime(timezone=True), nullable=True)
