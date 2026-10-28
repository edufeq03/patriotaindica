import logging
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from backend.app.core.config import settings
from backend.app.core.database import get_db, set_db_app_context
from backend.app.core.rate_limit import check_rate_limit, get_client_ip
from backend.app.core.security import create_access_token, get_password_hash
from backend.app.models.business import Business
from backend.app.models.user import User
from backend.app.services.otp import hash_phone, normalize_e164, otp_service

logger = logging.getLogger("patriotaindica.claim")
router = APIRouter()


class OTPVerifyRequest(BaseModel):
    code: str = Field(..., min_length=6, max_length=6)


class PhoneOTPRequest(BaseModel):
    phone: str = Field(..., min_length=8, max_length=25)


class PhoneOTPVerifyRequest(BaseModel):
    phone: str = Field(..., min_length=8, max_length=25)
    code: str = Field(..., min_length=6, max_length=6)


@router.post("/request-otp-by-phone")
async def request_otp_by_phone(
    payload: PhoneOTPRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """
    SEGURANÇA (T1.1 & H2 Anti-enumeração):
    - Normaliza telefone para formato E.164 (+55...)
    - Rate limit estrito: 10 requisições por hora por IP e 3 requisições por hora por número (hash SHA-256)
    - Busca por igualdade exata na coluna indexada whatsapp_e164
    - Resposta idêntica e genérica independente de o número existir ou não no banco (previne enumeração de lojistas)
    - Código NUNCA é retornado na resposta HTTP
    """
    client_ip = get_client_ip(request)
    await check_rate_limit(
        key=f"ratelimit:otp:ip:{client_ip}",
        limit=10,
        window_seconds=3600,
        error_msg="Limite de solicitações de verificação por IP excedido (máximo 10 por hora). Tente mais tarde.",
    )

    phone_e164 = normalize_e164(payload.phone)
    if not phone_e164:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Número de telefone inválido. Informe DDD + número completo com 10 ou 11 dígitos.",
        )

    phone_hash = hash_phone(phone_e164)
    await check_rate_limit(
        key=f"ratelimit:otp:phone:{phone_hash}",
        limit=3,
        window_seconds=3600,
        error_msg="Limite de envios excedido para este número (máximo 3 por hora). Tente novamente em 1 hora.",
    )

    # Busca exata usando a coluna normalizada whatsapp_e164 (ou whatsapp se migration ainda em curso)
    stmt = (
        select(Business.id, Business.name, Business.whatsapp_e164, Business.whatsapp)
        .where(
            (Business.whatsapp_e164 == phone_e164)
            | (Business.whatsapp == payload.phone)
            | (Business.whatsapp == phone_e164)
        )
        .order_by(Business.created_at.desc())
    )
    result = await db.execute(stmt)
    matching_businesses = result.all()

    if matching_businesses:
        primary_biz = matching_businesses[0]
        biz_name = getattr(primary_biz, "name", None) or (primary_biz[1] if isinstance(primary_biz, (tuple, list)) and len(primary_biz) > 1 else "Patriota Indica")
        try:
            await otp_service.request_otp_by_e164(
                phone_e164=phone_e164,
                business_name=biz_name,
            )
        except Exception as e:
            logger.error("Falha no envio do WhatsApp OTP: %s", e)
            # Não expõe detalhe interno do provedor
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Não foi possível enviar o código via WhatsApp no momento. Tente novamente mais tarde.",
            )

    # Resposta SEMPRE genérica para evitar enumeração e vazamento de dados de empresas cadastradas
    return {
        "success": True,
        "message": "Se o número estiver cadastrado, você receberá um código de verificação via WhatsApp.",
        "expires_in_seconds": 300,
    }


@router.post("/verify-otp")
async def verify_otp_by_phone(
    payload: PhoneOTPVerifyRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    SEGURANÇA (T1.1 & H3 Pre-hijacking prevention):
    - Valida o código OTP para o telefone normalizado E.164
    - Máximo de 5 tentativas (código destruído na 5ª falha)
    - Sucesso grava whatsapp_verified_at
    - Status de curadoria e is_verified NUNCA são alterados por esta rota
    - Prevenção de account pre-hijacking (H3): cria usuário NOVO e exclusivo com e-mail sintético não colidível,
      nunca busca usuário existente por telefone não verificado
    """
    phone_e164 = normalize_e164(payload.phone)
    if not phone_e164:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Número de telefone inválido.",
        )

    valid, message = otp_service.verify_otp_by_e164(
        phone_e164=phone_e164,
        submitted_code=payload.code,
    )
    if not valid:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=message)

    # Localiza as empresas cadastradas com este número
    stmt = (
        select(Business)
        .where(
            (Business.whatsapp_e164 == phone_e164)
            | (Business.whatsapp == payload.phone)
            | (Business.whatsapp == phone_e164)
        )
        .order_by(Business.created_at.desc())
    )
    businesses = (await db.execute(stmt)).scalars().all()
    if not businesses:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Nenhuma empresa associada a este número de telefone foi encontrada.",
        )

    primary_biz = businesses[0]
    now = datetime.now(timezone.utc)

    # Atualiza whatsapp_verified_at em todos os negócios desse telefone
    for b in businesses:
        b.whatsapp_verified_at = now
        if not b.whatsapp_e164:
            b.whatsapp_e164 = phone_e164

    # H3: Obter usuário existente APENAS se já era o dono vinculado da empresa (por ID)
    owner_user = None
    if primary_biz.owner_user_id:
        u_stmt = select(User).where(User.id == primary_biz.owner_user_id)
        owner_user = (await db.execute(u_stmt)).scalars().first()

    if not owner_user:
        # Cria usuário novo e exclusivo com e-mail sintético não colidível (H3)
        synthetic_email = f"owner-{primary_biz.id.hex[:8]}-{secrets.token_hex(4)}@patriotaindica.internal"
        owner_user = User(
            id=uuid.uuid4(),
            name=primary_biz.name,
            email=synthetic_email,
            phone=phone_e164,
            password_hash=get_password_hash(secrets.token_urlsafe(32)),
            role="owner",
            is_active=True,
        )
        db.add(owner_user)
        await db.flush()

        for b in businesses:
            if not b.owner_user_id:
                b.owner_user_id = owner_user.id
    else:
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
        "business_id": str(primary_biz.id),
        "user": {
            "id": str(owner_user.id),
            "name": owner_user.name,
            "email": owner_user.email,
            "role": owner_user.role,
        },
    }


@router.post("/{business_id}/request-otp")
async def request_claim_otp(
    business_id: UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """
    Dispara envio de código OTP para o WhatsApp cadastrado de uma empresa específica.
    SEGURANÇA (T1.1): Código NUNCA é retornado na resposta HTTP.
    """
    client_ip = get_client_ip(request)
    await check_rate_limit(
        key=f"ratelimit:otp:ip:{client_ip}",
        limit=10,
        window_seconds=3600,
        error_msg="Limite de solicitações de verificação por IP excedido. Tente mais tarde.",
    )

    stmt = select(Business.id, Business.name, Business.whatsapp, Business.whatsapp_e164).where(Business.id == business_id)
    row = (await db.execute(stmt)).first()
    if not row:
        raise HTTPException(status_code=404, detail="Empresa não encontrada.")

    b_id = row[0]
    b_name = row[1]
    b_whatsapp = row[2]
    b_e164 = row[3] if len(row) > 3 else None
    phone_e164 = b_e164 or normalize_e164(b_whatsapp)

    if not phone_e164:
        raise HTTPException(status_code=400, detail="Esta empresa não possui número de WhatsApp válido cadastrado.")

    phone_hash = hash_phone(phone_e164)
    await check_rate_limit(
        key=f"ratelimit:otp:phone:{phone_hash}",
        limit=3,
        window_seconds=3600,
        error_msg="Limite de envios excedido para este número. Tente novamente em 1 hora.",
    )

    try:
        success, message = await otp_service.request_otp_by_e164(
            phone_e164=phone_e164,
            business_name=b_name,
        )
    except Exception as e:
        logger.error("Erro no envio WhatsApp: %s", e)
        success = False
        message = str(e)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=message or "Não foi possível enviar o código via WhatsApp. Tente novamente mais tarde.",
        )

    return {
        "success": True,
        "message": message,
        "masked_phone": otp_service.mask_phone(phone_e164),
        "expires_in_seconds": 300,
    }


@router.post("/{business_id}/verify-otp")
async def verify_claim_otp(
    business_id: UUID,
    payload: OTPVerifyRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Valida código OTP para uma empresa específica.
    Garante que status e is_verified NUNCA são alterados.
    """
    stmt = select(Business).where(Business.id == business_id)
    business = (await db.execute(stmt)).scalar_one_or_none()
    if not business:
        raise HTTPException(status_code=404, detail="Empresa não encontrada.")

    phone_e164 = business.whatsapp_e164 or normalize_e164(business.whatsapp)
    if not phone_e164:
        raise HTTPException(status_code=400, detail="Empresa não possui telefone WhatsApp válido.")

    valid, message = otp_service.verify_otp_by_e164(
        phone_e164=phone_e164,
        submitted_code=payload.code,
    )
    if not valid:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=message)

    now = datetime.now(timezone.utc)
    business.whatsapp_verified_at = now
    if not business.whatsapp_e164:
        business.whatsapp_e164 = phone_e164

    owner_user = None
    if business.owner_user_id:
        u_stmt = select(User).where(User.id == business.owner_user_id)
        owner_user = (await db.execute(u_stmt)).scalars().first()

    if not owner_user:
        synthetic_email = f"owner-{business.id.hex[:8]}-{secrets.token_hex(4)}@patriotaindica.internal"
        owner_user = User(
            id=uuid.uuid4(),
            name=business.name,
            email=synthetic_email,
            phone=phone_e164,
            password_hash=get_password_hash(secrets.token_urlsafe(32)),
            role="owner",
            is_active=True,
        )
        db.add(owner_user)
        await db.flush()
        business.owner_user_id = owner_user.id
    else:
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
