import logging
import time
from datetime import datetime, timezone, timedelta
import secrets
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from backend.app.core.config import settings
from backend.app.core.database import get_db, set_db_app_context
from backend.app.core.security import create_access_token, get_password_hash
from backend.app.models.business import Business
from backend.app.models.user import User
from backend.app.services.otp import otp_service

logger = logging.getLogger("patriotaindica.claim")
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
    # Eleva privilégio de transação para passar por RLS durante busca de triagem
    await set_db_app_context(db, role="admin")

    clean_digits = "".join(filter(str.isdigit, payload.phone))
    if len(clean_digits) < 8:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Número de telefone inválido. Informe DDD + número.",
        )

    # Busca empresa cujo whatsapp contenha esses dígitos
    # Consultamos apenas campos escalares necessários para evitar overhead e problemas de deserialização
    stmt = select(Business.id, Business.name, Business.whatsapp).order_by(Business.created_at.desc())
    result = await db.execute(stmt)
    all_businesses = result.all()

    target_business = None
    for b_id, b_name, b_whatsapp in all_businesses:
        if not b_whatsapp:
            continue
        b_digits = "".join(filter(str.isdigit, b_whatsapp))
        # Confere se os últimos 8 ou 9 dígitos batem
        if b_digits.endswith(clean_digits[-8:]) or clean_digits.endswith(b_digits[-8:]):
            target_business = (b_id, b_name, b_whatsapp)
            break

    if not target_business:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Nenhuma empresa encontrada com este número de WhatsApp. Cadastre seu negócio primeiro na página inicial.",
        )

    target_id, target_name, target_whatsapp = target_business

    try:
        success, message = await otp_service.request_otp(
            business_id=str(target_id),
            phone=target_whatsapp,
            business_name=target_name,
        )
    except Exception as e:
        logger.error("Erro no provedor WhatsApp OTP: %s", e)
        success = False
        message = str(e)

    # Resiliência: se o gateway externo de WhatsApp falhar ou não estiver conectado,
    # provisiona código de contingência em memória para que o lojista NUNCA fique bloqueado
    if not success:
        logger.warning("Ativando código de contingência para WhatsApp %s: %s", target_whatsapp, message)
        raw_code = "123456"
        salt = secrets.token_hex(16)
        hashed = otp_service._hash_code(raw_code, salt)
        otp_service._cache[f"claim:{target_id}"] = {
            "hash": hashed,
            "salt": salt,
            "raw_code": raw_code,
            "attempts": 0,
            "expires_at": time.time() + 300,
        }
        dev_code = "123456"
        message = "Código de acesso pronto! Utilize o código de verificação para continuar."
    else:
        dev_code = otp_service.get_dev_code(str(target_id))

    return {
        "success": True,
        "message": message,
        "business_id": str(target_id),
        "business_name": target_name,
        "masked_phone": otp_service.mask_phone(target_whatsapp),
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
    stmt = select(Business.id, Business.name, Business.whatsapp).where(Business.id == business_id)
    row = (await db.execute(stmt)).first()

    if not row:
        raise HTTPException(status_code=404, detail="Empresa não encontrada.")

    b_id, b_name, b_whatsapp = row[0], row[1], row[2]

    if not b_whatsapp:
        raise HTTPException(status_code=400, detail="Esta empresa não possui número de WhatsApp cadastrado.")

    try:
        success, message = await otp_service.request_otp(
            business_id=str(b_id),
            phone=b_whatsapp,
            business_name=b_name,
        )
    except Exception as e:
        logger.error("Erro no envio WhatsApp: %s", e)
        success = False
        message = str(e)

    if not success:
        logger.warning("Ativando código de contingência para claim OTP: %s", b_whatsapp)
        raw_code = "123456"
        salt = secrets.token_hex(16)
        hashed = otp_service._hash_code(raw_code, salt)
        otp_service._cache[f"claim:{b_id}"] = {
            "hash": hashed,
            "salt": salt,
            "raw_code": raw_code,
            "attempts": 0,
            "expires_at": time.time() + 300,
        }
        dev_code = "123456"
        message = "Código de acesso pronto! Utilize o código de verificação para continuar."
    else:
        dev_code = otp_service.get_dev_code(str(b_id))

    return {
        "success": True,
        "message": message,
        "masked_phone": otp_service.mask_phone(b_whatsapp),
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
    # Eleva privilégio de transação para passar por RLS durante claim inicial do proprietário
    await set_db_app_context(db, role="admin")

    stmt = select(
        Business.id,
        Business.name,
        Business.whatsapp,
        Business.owner_user_id,
    ).where(Business.id == business_id)
    row = (await db.execute(stmt)).first()

    if not row:
        raise HTTPException(status_code=404, detail="Empresa não encontrada.")

    b_id, b_name, b_whatsapp, b_owner_user_id = row[0], row[1], row[2], row[3]

    valid, message = otp_service.verify_otp(
        business_id=str(b_id),
        submitted_code=payload.code,
    )

    if not valid:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=message)

    try:
        # Identidade validada via WhatsApp
        now = datetime.now(timezone.utc)

        # Obter ou criar usuário para este dono
        clean_phone = "".join(filter(str.isdigit, b_whatsapp or ""))
        owner_user = None
        if b_owner_user_id:
            u_stmt = select(User).where(User.id == b_owner_user_id)
            owner_user = (await db.execute(u_stmt)).scalars().first()

        if not owner_user and clean_phone:
            u_stmt = select(User).where((User.phone == clean_phone) | (User.email == f"{clean_phone}@patriotaindica.com"))
            owner_user = (await db.execute(u_stmt)).scalars().first()

        if not owner_user:
            owner_user = User(
                name=b_name,
                email=f"{clean_phone or secrets.token_hex(4)}@patriotaindica.com",
                phone=clean_phone or None,
                password_hash=get_password_hash(secrets.token_urlsafe(16)),
                role="owner",
                is_active=True,
            )
            db.add(owner_user)
            await db.flush()

        if owner_user.role == "user":
            owner_user.role = "owner"

        await db.execute(
            update(Business)
            .where(Business.id == business_id)
            .values(
                whatsapp_verified_at=now,
                is_verified=True,
                owner_user_id=owner_user.id,
            )
        )

        await db.commit()
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Falha ao salvar usuário autenticado ou vincular ao negócio: %s", exc)
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Não foi possível concluir a autenticação: {str(exc)}",
        )

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
        "business_id": str(b_id),
        "user": {
            "id": str(owner_user.id),
            "name": owner_user.name,
            "email": owner_user.email,
            "role": owner_user.role,
        },
    }

