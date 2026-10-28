from datetime import datetime
from typing import List, Optional
from uuid import UUID
from pydantic import BaseModel, ConfigDict, EmailStr, Field


# Users & Auth
class UserBase(BaseModel):
    name: str = Field(..., min_length=2, max_length=150)
    email: EmailStr
    phone: Optional[str] = Field(None, max_length=20)
    role: str = "user"


class UserCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=150)
    email: EmailStr
    phone: Optional[str] = Field(None, max_length=20)
    password: str = Field(..., min_length=12, max_length=100)
    model_config = ConfigDict(extra="forbid")



class UserOut(UserBase):
    id: UUID
    is_active: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: Optional[str] = None
    token_type: str = "bearer"
    user: Optional[UserOut] = None


class RefreshTokenRequest(BaseModel):
    refresh_token: str
    model_config = ConfigDict(extra="forbid")


class LogoutRequest(BaseModel):
    refresh_token: Optional[str] = None
    model_config = ConfigDict(extra="forbid")


# Triagem e Ações Administrativas
class TriageDecisionRequest(BaseModel):
    action: str  # 'approve', 'request_changes', 'reject', 'suspend'
    note: Optional[str] = None
    is_verified: Optional[bool] = None
    confirm_duplicate_document: bool = False
    lat: Optional[float] = None
    lng: Optional[float] = None


class TriageChecklistResult(BaseModel):
    cnpj_valid: Optional[bool] = None
    cnpj_situation: Optional[str] = None
    whatsapp_verified: bool = False
    geocoding_valid: bool = False
    duplicate_detected: bool = False
    duplicate_business_id: Optional[UUID] = None
    notes: List[str] = []


# Eventos de Redirecionamento
class ContactRedirectEvent(BaseModel):
    business_id: UUID
    event_type: str  # 'whatsapp', 'phone', 'website'
    city: Optional[str] = None
    target_url: str
