from datetime import datetime
from typing import List, Optional
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field
from backend.app.schemas.category import CategoryOut


class BusinessBase(BaseModel):
    name: str
    description: Optional[str] = None
    listing_type: str = "service"  # 'service', 'product', 'both'

    # Contatos
    whatsapp: str
    phone: Optional[str] = None
    website: Optional[str] = None
    instagram: Optional[str] = None

    # Localização
    street: Optional[str] = None
    number: Optional[str] = None
    neighborhood: str
    city: str
    state: str = Field(..., max_length=2)
    postal_code: Optional[str] = None
    show_full_address: bool = False
    latitude: float
    longitude: float

    service_mode: str = "at_location"  # 'at_location', 'at_customer', 'both', 'online'
    service_radius_km: Optional[int] = None

    logo_url: Optional[str] = None
    banner_url: Optional[str] = None


class BusinessPublicCard(BaseModel):
    id: UUID
    name: str
    slug: str
    description: Optional[str] = None
    listing_type: str
    service_mode: str
    service_radius_km: Optional[int] = None
    category_name: Optional[str] = None
    whatsapp: str
    phone: Optional[str] = None
    neighborhood: str
    city: str
    state: str
    street: Optional[str] = None
    number: Optional[str] = None
    show_full_address: bool
    logo_url: Optional[str] = None
    banner_url: Optional[str] = None
    is_verified: bool
    distance_km: Optional[float] = None


class BusinessDetail(BaseModel):
    id: UUID
    name: str
    slug: str
    description: Optional[str] = None
    listing_type: str
    service_mode: str
    service_radius_km: Optional[int] = None
    whatsapp: str
    phone: Optional[str] = None
    website: Optional[str] = None
    instagram: Optional[str] = None
    neighborhood: str
    city: str
    state: str
    street: Optional[str] = None
    number: Optional[str] = None
    show_full_address: bool
    logo_url: Optional[str] = None
    banner_url: Optional[str] = None
    is_verified: bool
    categories: List[CategoryOut] = []
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class BusinessApplicationCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=150)
    description: Optional[str] = Field(None, max_length=2000)
    document_type: Optional[str] = Field("CNPJ", max_length=10)
    document_number: Optional[str] = Field(None, max_length=20)
    whatsapp: str = Field(..., min_length=8, max_length=20)
    phone: Optional[str] = Field(None, max_length=20)
    website: Optional[str] = Field(None, max_length=255)
    instagram: Optional[str] = Field(None, max_length=100)
    street: Optional[str] = Field(None, max_length=150)
    number: Optional[str] = Field(None, max_length=30)
    neighborhood: str = Field(..., min_length=1, max_length=100)
    city: str = Field(..., min_length=2, max_length=100)
    state: str = Field(..., min_length=2, max_length=2)
    postal_code: Optional[str] = Field(None, max_length=10)
    show_full_address: bool = False
    latitude: Optional[float] = Field(None, ge=-90.0, le=90.0)
    longitude: Optional[float] = Field(None, ge=-180.0, le=180.0)
    service_mode: str = Field("at_location", max_length=20)
    service_radius_km: Optional[int] = Field(None, ge=1, le=500)
    category_ids: List[UUID] = []
    primary_category_id: Optional[UUID] = None

