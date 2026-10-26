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


class UserCreate(UserBase):
    password: str = Field(..., min_length=8, max_length=100)



class UserOut(UserBase):
    id: UUID
    is_active: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


# Triagem e Ações Administrativas
class TriageDecisionRequest(BaseModel):
    action: str  # 'approve', 'request_changes', 'reject', 'suspend'
    note: Optional[str] = None
    is_verified: Optional[bool] = None


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
