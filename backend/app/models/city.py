import uuid
from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from geoalchemy2 import Geography
from backend.app.core.database import Base


class City(Base):
    __tablename__ = "cities"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(100), nullable=False)
    state = Column(String(2), nullable=False)
    slug = Column(String(120), unique=True, nullable=False, index=True)
    status = Column(String(20), nullable=False, default="soon", index=True)  # 'active', 'soon'
    location = Column(Geography(geometry_type="POINT", srid=4326), nullable=True)
    interested_count = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    waitlist_entries = relationship("CityWaitlist", back_populates="city", cascade="all, delete-orphan")


class CityWaitlist(Base):
    __tablename__ = "city_waitlist"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    city_id = Column(UUID(as_uuid=True), ForeignKey("cities.id", ondelete="CASCADE"), nullable=False, index=True)
    contact = Column(String(100), nullable=False)
    is_business = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    city = relationship("City", back_populates="waitlist_entries")
