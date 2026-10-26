from datetime import datetime
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, ConfigDict


class CategoryBase(BaseModel):
    name: str
    slug: str
    kind: str = "both"  # 'service', 'product', 'both'
    icon_name: Optional[str] = None
    display_order: int = 0
    parent_id: Optional[UUID] = None


class CategoryCreate(CategoryBase):
    pass


class CategoryOut(CategoryBase):
    id: UUID
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
