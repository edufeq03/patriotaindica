from datetime import datetime, timezone, timedelta
import secrets
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from backend.app.core.config import settings
from backend.app.core.database import get_db
from backend.app.core.security import create_access_token, get_password_hash
from backend.app.models.business import Business
from backend.app.models.user import User
from backend.app.services.otp import otp_service

router = APIRouter()


class OTPVerifyRequest(BaseModel):
    code: str = Field(..., min_length=6, max_length=6)


class PhoneOTPRequest(BaseModel):
    phone: str = Field(..., min_length=8, max_length=25)


@router.post("/request-otp-by-phone")
async def request_otp_by_phone(
    payload: PhoneOTPRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Localiza a empresa pelo número de WhatsApp informado e dispara o envio do código OTP.
    Permite login ágil e seguro sem necessidade de memorizar senha.
    """
    clean_digits = "".join(filter(str.isdigit, payload.phone))
    if len(clean_digits) < 8:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Número de telefone inválido. Informe DDD + número.",
        )

    # Busca empresa cujo whatsapp contenha esses dígitos
    stmt = select(Business).order_by(Business.created_at.desc())
    result = await db.execute(stmt)
    all_businesses = result.scalars().all()

    target_business = None
    for b in all_businesses:
        if not b.whatsapp:
            continue
        b_digits = "".join(filter(str.isdigit, b.whatsapp))
        # Confere se os últimos 8 ou 9 dígitos batem
        if b_digits.endswith(clean_digits[-8:]) or clean_digits.endswith(b_digits[-8:]):
            target_business = b
            break

    if not target_business:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Nenhuma empresa encontrada com este número de WhatsApp. Cadastre seu negócio primeiro na página inicial.",
        )

    success, message = await otp_service.request_otp(
        business_id=str(target_business.id),
        phone=target_business.whatsapp,
        business_name=target_business.name,
    )

    if not success:
        status_code = status.HTTP_429_TOO_MANY_REQUESTS if "Limite" in message else status.HTTP_500_INTERNAL_SERVER_ERROR
        raise HTTPException(status_code=status_code, detail=message)

    dev_code = otp_service.get_dev_code(str(target_business.id))

    return {
        "success": True,
        "message": message,
        "business_id": str(target_business.id),
        "business_name": target_business.name,
        "masked_phone": otp_service.mask_phone(target_business.whatsapp),
        "dev_code": dev_code,
        "expires_in_seconds": 300,
    }


@router.post("/{business_id}/request-otp")
async def request_claim_otp(
    business_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """
    Dispara o envio de código OTP via WhatsApp oficial cadastrado da empresa.
    SEGURANÇA (C4): O código oficial NUNCA é retornado no corpo da resposta HTTP.
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

    dev_code = otp_service.get_dev_code(str(business.id))

    return {
        "success": True,
        "message": message,
        "masked_phone": otp_service.mask_phone(business.whatsapp),
        "dev_code": dev_code,
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
    Se válido, vincula o proprietário ao negócio e retorna um token JWT de autenticação para acesso imediato.
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

    # Identidade validada via WhatsApp
    now = datetime.now(timezone.utc)
    business.whatsapp_verified_at = now
    business.is_verified = True

    # Obter ou criar usuário para este dono
    clean_phone = "".join(filter(str.isdigit, business.whatsapp or ""))
    owner_user = None
    if business.owner_user_id:
        u_stmt = select(User).where(User.id == business.owner_user_id)
        owner_user = (await db.execute(u_stmt)).scalar_one_or_none()

    if not owner_user and clean_phone:
        u_stmt = select(User).where((User.phone == clean_phone) | (User.email == f"{clean_phone}@patriotaindica.com"))
        owner_user = (await db.execute(u_stmt)).scalar_one_or_none()

    if not owner_user:
        owner_user = User(
            name=business.name,
            email=f"{clean_phone or secrets.token_hex(4)}@patriotaindica.com",
            phone=clean_phone or None,
            password_hash=get_password_hash(secrets.token_urlsafe(16)),
            role="owner",
            is_active=True,
        )
        db.add(owner_user)
        await db.flush()

    business.owner_user_id = owner_user.id
    if owner_user.role == "user":
        owner_user.role = "owner"

    await db.commit()

    access_token = create_access_token(
        subject=owner_user.id,
        role=owner_user.role,
        expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
    )

    return {
        "success": True,
        "message": "Identidade confirmada com sucesso via WhatsApp! Acesso liberado ao painel.",
        "access_token": access_token,
        "token_type": "bearer",
        "business_id": str(business.id),
        "user": {
            "id": str(owner_user.id),
            "name": owner_user.name,
            "email": owner_user.email,
            "role": owner_user.role,
        },
    }
