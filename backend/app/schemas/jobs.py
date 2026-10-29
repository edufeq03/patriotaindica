import re
import unicodedata
from datetime import datetime
from typing import List, Literal, Optional
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field, field_validator

JobContractType = Literal[
    "clt",
    "temporario",
    "meio_periodo",
    "estagio",
    "aprendiz",
    "autonomo",
]

JobStatus = Literal[
    "pending_review",
    "active",
    "expired",
    "closed",
    "rejected",
]

JobCloseReason = Literal[
    "hired_here",
    "hired_other",
    "gave_up",
    "other",
]

# Padrões de validação segura de texto (Seção 5.1)
URL_PATTERN = re.compile(r"(https?://|www\.|\.com|\.br|@)", re.IGNORECASE)
PHONE_PATTERN = re.compile(r"(\(?\d{2}\)?\s*9?\d{4}[-\s]?\d{4})")
FOUR_DIGITS_PATTERN = re.compile(r"\b\d{4,}\b")
CURRENCY_PATTERN = re.compile(r"R\$\s*\d+", re.IGNORECASE)
REPETITIVE_PATTERN = re.compile(r"(.)\1{3,}")


def sanitize_job_text(text: str, max_length: int, field_name: str) -> str:
    if not text:
        return ""
    normalized = unicodedata.normalize("NFKC", text).strip()
    normalized = re.sub(r"\s+", " ", normalized)

    if len(normalized) > max_length:
        raise ValueError(f"O campo '{field_name}' deve ter no máximo {max_length} caracteres.")

    if URL_PATTERN.search(normalized):
        raise ValueError(f"O campo '{field_name}' não pode conter links ou e-mails.")

    if PHONE_PATTERN.search(normalized) or FOUR_DIGITS_PATTERN.search(normalized):
        raise ValueError(f"O campo '{field_name}' não pode conter números de telefone ou sequências de dígitos.")

    if CURRENCY_PATTERN.search(normalized):
        raise ValueError(f"O campo '{field_name}' não deve conter valores em reais (R$). Descreva as funções da vaga.")

    if REPETITIVE_PATTERN.search(normalized):
        raise ValueError(f"O campo '{field_name}' contém caracteres repetitivos inválidos.")

    # Caixa alta excessiva (> 70% quando comprimento >= 10)
    letters = [c for c in normalized if c.isalpha()]
    if len(letters) >= 10:
        upper_letters = [c for c in letters if c.isupper()]
        if len(upper_letters) / len(letters) > 0.70:
            raise ValueError(f"O campo '{field_name}' não deve ser escrito predominantemente em letras maiúsculas.")

    return normalized


class JobCreate(BaseModel):
    title: str = Field(..., min_length=3, max_length=60)
    description: Optional[str] = Field(None, max_length=280)
    contract_type: JobContractType = "clt"
    openings_count: int = Field(1, ge=1, le=20)

    model_config = ConfigDict(extra="forbid")

    @field_validator("title")
    @classmethod
    def validate_title(cls, v: str) -> str:
        clean = sanitize_job_text(v, 60, "Título da Vaga")
        if len(clean) < 3:
            raise ValueError("O título da vaga deve ter pelo menos 3 caracteres.")
        return clean

    @field_validator("description")
    @classmethod
    def validate_description(cls, v: Optional[str]) -> Optional[str]:
        if not v or not v.strip():
            return None
        return sanitize_job_text(v, 280, "Descrição da Vaga")


class JobUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=3, max_length=60)
    description: Optional[str] = Field(None, max_length=280)
    contract_type: Optional[JobContractType] = None
    openings_count: Optional[int] = Field(None, ge=1, le=20)

    model_config = ConfigDict(extra="forbid")

    @field_validator("title")
    @classmethod
    def validate_title(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        clean = sanitize_job_text(v, 60, "Título da Vaga")
        if len(clean) < 3:
            raise ValueError("O título da vaga deve ter pelo menos 3 caracteres.")
        return clean

    @field_validator("description")
    @classmethod
    def validate_description(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        if not v.strip():
            return None
        return sanitize_job_text(v, 280, "Descrição da Vaga")


class JobClose(BaseModel):
    close_reason: JobCloseReason = "hired_here"

    model_config = ConfigDict(extra="forbid")


class JobOut(BaseModel):
    id: UUID
    business_id: UUID
    title: str
    description: Optional[str] = None
    contract_type: str
    openings_count: int
    status: str
    owner_paused: bool
    admin_hold: bool
    moderation_flags: List[str] = []
    published_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    renewed_count: int = 0
    close_reason: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PublicJobBusiness(BaseModel):
    id: UUID
    name: str
    slug: str
    logo_url: Optional[str] = None
    city: str
    neighborhood: str
    category_name: Optional[str] = None
    distance_km: Optional[float] = None

    model_config = ConfigDict(from_attributes=True)


class PublicJobCard(BaseModel):
    id: UUID
    title: str
    description: Optional[str] = None
    contract_type: str
    openings_count: int
    published_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    business: PublicJobBusiness

    model_config = ConfigDict(from_attributes=True)


class JobReportCreate(BaseModel):
    reason: Literal["golpe", "discriminacao", "improprio", "outro"]
    details: Optional[str] = Field(None, max_length=200)
    turnstile_token: Optional[str] = None

    model_config = ConfigDict(extra="forbid")
