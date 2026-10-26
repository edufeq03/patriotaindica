from typing import List, Optional
from uuid import UUID
from pydantic import BaseModel, Field


class SearchQueryParams(BaseModel):
    lat: float = Field(..., description="Latitude do usuário")
    lng: float = Field(..., description="Longitude do usuário")
    radius_km: float = Field(50.0, description="Raio de busca em km")
    q: Optional[str] = Field(None, description="Termo de busca textual")
    category_id: Optional[UUID] = Field(None, description="Filtrar por UUID de categoria")
    listing_type: Optional[str] = Field(None, description="'service', 'product', ou 'both'")
    page: int = Field(1, ge=1)
    limit: int = Field(20, ge=1, le=100)


class SearchResultSummary(BaseModel):
    total_found: int
    page: int
    limit: int
    has_more: bool
    businesses: List[dict]
