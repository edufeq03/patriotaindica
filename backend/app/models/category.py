import uuid
from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.dialects.postgresql import ENUM, UUID
from sqlalchemy.orm import relationship
from backend.app.core.database import Base

listing_type_enum = ENUM("service", "product", "both", name="listing_type", create_type=False)


class Category(Base):
    __tablename__ = "categories"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    parent_id = Column(UUID(as_uuid=True), ForeignKey("categories.id", ondelete="SET NULL"), nullable=True)
    name = Column(String(100), unique=True, nullable=False)
    slug = Column(String(100), unique=True, nullable=False, index=True)
    kind = Column(listing_type_enum, nullable=False, default="both")  # 'service', 'product', 'both'
    icon_name = Column(String(50), nullable=True)
    display_order = Column(Integer, nullable=False, default=0)
    status = Column(String(20), nullable=False, default="approved")  # 'approved', 'pending', 'rejected'
    proposed_by_business_id = Column(UUID(as_uuid=True), ForeignKey("businesses.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    children = relationship("Category", backref="parent", remote_side=[id])
    businesses = relationship("BusinessCategory", back_populates="category")
    aliases = relationship("CategoryAlias", back_populates="category", cascade="all, delete-orphan")


class CategoryAlias(Base):
    __tablename__ = "category_aliases"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    category_id = Column(UUID(as_uuid=True), ForeignKey("categories.id", ondelete="CASCADE"), nullable=False)
    alias_name = Column(String(100), unique=True, nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    category = relationship("Category", back_populates="aliases")
