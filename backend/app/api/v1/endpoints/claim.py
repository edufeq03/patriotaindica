from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from backend.app.core.database import get_db
from backend.app.models.business import Business
from backend.app.services.otp import otp_service

router = APIRouter()


class OTPVerifyRequest(BaseModel):
    code: str = Field(..., min_length=6, max_length=6)


@router.post("/{business_id}/request-otp")
async def request_claim_otp(
    business_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """
    Dispara o envio de código OTP via WhatsApp oficial cadastrado da empresa.
    SEGURANÇA (C4): O código NUNCA é retornado no corpo da resposta HTTP.
    """
    stmt = select(Business).where(Business.id == business_id)
    business = (await db.execute(stmt)).scalar_one_or_none()

    if not business:
        raise HTTPException(status_code=404, detail="Empresa não encontrada.")

    if not business.whatsapp:
        raise HTTPException(status_code=400, detail="Esta empresa não possui número de WhatsApp cadastrado.")

    success, message = await otp_service.request_otp(
        business_id=str(business.id),
        phone=business.whatsapp,
        business_name=business.name,
    )

    if not success:
        status_code = status.HTTP_429_TOO_MANY_REQUESTS if "Limite" in message else status.HTTP_500_INTERNAL_SERVER_ERROR
        raise HTTPException(status_code=status_code, detail=message)

    return {
        "success": True,
        "message": message,
        "masked_phone": otp_service.mask_phone(business.whatsapp),
        "expires_in_seconds": 300,
    }


@router.post("/{business_id}/verify-otp")
async def verify_claim_otp(
    business_id: UUID,
    payload: OTPVerifyRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Valida o código OTP informado pelo usuário contra o hash com sal armazenado no servidor.
    Bloqueia automaticamente após 5 tentativas incorretas.
    """
    stmt = select(Business).where(Business.id == business_id)
    business = (await db.execute(stmt)).scalar_one_or_none()

    if not business:
        raise HTTPException(status_code=404, detail="Empresa não encontrada.")

    valid, message = otp_service.verify_otp(
        business_id=str(business.id),
        submitted_code=payload.code,
    )

    if not valid:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=message)

    return {
        "success": True,
        "message": "Identidade confirmada com sucesso. Gestão autorizada.",
        "business_id": business.id,
    }
