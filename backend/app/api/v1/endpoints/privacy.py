import hashlib
from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.database import get_db
from backend.app.core.rate_limit import check_rate_limit, get_client_ip
from backend.app.core.security import get_current_active_admin
from backend.app.models.events import DataSubjectRequest
from backend.app.models.user import User

router = APIRouter()


class PrivacyRequestCreate(BaseModel):
    request_type: str = Field(..., pattern="^(deletion|revocation|export|correction|information)$")
    email: EmailStr
    phone: Optional[str] = Field(None, max_length=32)
    details: Optional[str] = Field(None, max_length=2000)


class PrivacyRequestResponse(BaseModel):
    id: UUID
    request_type: str
    email: str
    status: str
    message: str


class PrivacyAdminResponse(BaseModel):
    id: UUID
    request_type: str
    email: str
    phone: Optional[str]
    details: Optional[str]
    status: str
    created_at: str


@router.post("/request", response_model=PrivacyRequestResponse, status_code=status.HTTP_201_CREATED)
async def submit_privacy_request(
    payload: PrivacyRequestCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """
    CONFORMIDADE LGPD (M11): Canal formal do Titular de Dados (Art. 18 da Lei 13.709/2018).
    Permite solicitar exclusão de perfil, revogação do consentimento da Carta de Princípios,
    exportação de dados ou correção cadastral.
    """
    client_ip = get_client_ip(request)
    await check_rate_limit(
        key=f"privacy_req:{client_ip}",
        limit=10,
        window_seconds=3600,
        error_msg="Muitas solicitações de privacidade enviadas. Tente novamente mais tarde.",
    )
    ip_hash = hashlib.sha256(client_ip.encode("utf-8")).hexdigest()

    import uuid

    req = DataSubjectRequest(
        id=uuid.uuid4(),
        request_type=payload.request_type,
        email=str(payload.email).lower(),
        phone=payload.phone.strip() if payload.phone else None,
        details=payload.details.strip() if payload.details else None,
        status="received",
        ip_hash=ip_hash,
    )
    db.add(req)
    await db.commit()
    await db.refresh(req)

    return PrivacyRequestResponse(
        id=req.id,
        request_type=req.request_type,
        email=req.email,
        status=req.status,
        message="Solicitação registrada com sucesso sob conformidade LGPD. Prazo legal de resposta de até 15 dias.",
    )


@router.get("/admin/requests", response_model=List[PrivacyAdminResponse])
async def list_privacy_requests_admin(
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(get_current_active_admin),
):
    """
    ADMIN/DPO: Visualizar fila de solicitações de titulares de dados.
    """
    stmt = select(DataSubjectRequest).order_by(desc(DataSubjectRequest.created_at)).limit(100)
    result = await db.execute(stmt)
    records = result.scalars().all()

    return [
        PrivacyAdminResponse(
            id=r.id,
            request_type=r.request_type,
            email=r.email,
            phone=r.phone,
            details=r.details,
            status=r.status,
            created_at=r.created_at.isoformat() if r.created_at else "",
        )
        for r in records
    ]
