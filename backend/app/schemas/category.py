from datetime import datetime
from typing import List, Literal, Optional
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field, field_validator
from backend.app.core.niche_validator import validate_and_normalize_niche_name


class CategoryBase(BaseModel):
    name: str
    slug: str
    kind: Literal["service", "product", "both"] = "both"
    icon_name: Optional[str] = None
    display_order: int = 0
    parent_id: Optional[UUID] = None
    status: str = "approved"


class CategoryCreate(CategoryBase):
    pass


class CategoryAdminCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    kind: Literal["service", "product", "both"] = "service"
    icon_name: Optional[str] = "wrench"
    display_order: Optional[int] = 0

    model_config = ConfigDict(extra="forbid")


class CategoryOut(CategoryBase):
    id: UUID
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CategorySuggestOut(BaseModel):
    id: UUID
    name: str
    slug: str
    kind: str
    is_alias: bool = False
    canonical_name: Optional[str] = None


class CategoryProposalCreate(BaseModel):
    """
    Criação/Proposta de novo nicho (Sec 4.2).
    """
    name: str = Field(..., min_length=3, max_length=60)
    kind: Literal["service", "product", "both"] = "both"
    parent_id: Optional[UUID] = None
    business_id: Optional[UUID] = None

    model_config = ConfigDict(extra="forbid")

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        return validate_and_normalize_niche_name(v)


class CategoryModerationAction(BaseModel):
    """
    Ação do analista/admin para moderação de nicho proposto (Sec 4).
    """
    action: Literal["approve", "merge", "reject"]
    adjusted_name: Optional[str] = None
    merged_into_category_id: Optional[UUID] = None
    icon_name: Optional[str] = "sparkles"

    model_config = ConfigDict(extra="forbid")
