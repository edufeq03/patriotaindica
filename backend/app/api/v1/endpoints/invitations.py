import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.database import get_db
from backend.app.core.rate_limit import check_rate_limit, get_client_ip
from backend.app.core.security import get_current_active_admin, get_current_user
from backend.app.models.business import Business
from backend.app.models.events import Invitation
from backend.app.models.user import User

router = APIRouter()


class InvitationCreateRequest(BaseModel):
    business_id: UUID
    phone: str
    days_valid: int = 7

    model_config = ConfigDict(extra="forbid")


def hash_token(raw_token: str) -> str:
    """Calcula o hash SHA-256 do token para armazenamento seguro."""
    return hashlib.sha256(raw_token.strip().encode("utf-8")).hexdigest()


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_secure_invitation(
    payload: InvitationCreateRequest,
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(get_current_active_admin),
):
    """
    SEGURANÇA (M12): Gera convite seguro baseado em hash SHA-256 (Canal B).
    - Token de 32 bytes gerado criptograficamente com secrets.token_urlsafe.
    - O banco armazena APENAS o hash SHA-256.
    - Expiração curta (padrão de 7 dias).
    - Uso único.
    """
    biz_stmt = select(Business).where(Business.id == payload.business_id)
    business = (await db.execute(biz_stmt)).scalar_one_or_none()
    if not business:
        raise HTTPException(status_code=404, detail="Empresa não encontrada.")

    raw_token = secrets.token_urlsafe(32)
    token_hash = hash_token(raw_token)
    expires_at = datetime.now(timezone.utc) + timedelta(days=payload.days_valid)

    invitation = Invitation(
        token_hash=token_hash,
        business_id=business.id,
        phone=payload.phone.strip(),
        expires_at=expires_at,
        created_by=current_admin.id,
    )
    db.add(invitation)
    await db.commit()

    return {
        "success": True,
        "raw_token": raw_token,
        "invite_url": f"/convite/{raw_token}",
        "expires_at": expires_at.isoformat(),
        "business_name": business.name,
    }


@router.get("/{raw_token}")
async def inspect_invitation(
    raw_token: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """
    SEGURANÇA (M12): Inspeção de convite com mitigação de enumeração e força bruta.
    - Rate limit estrito de 10 requisições por minuto por IP.
    """
    client_ip = get_client_ip(request)
    await check_rate_limit(
        key=f"ratelimit:invite_check:{client_ip}",
        limit=10,
        window_seconds=60,
        error_msg="Muitas tentativas de validação de convite. Tente novamente mais tarde.",
    )

    token_hash = hash_token(raw_token)
    now = datetime.now(timezone.utc)

    stmt = select(Invitation).where(
        Invitation.token_hash == token_hash,
        Invitation.expires_at > now,
        Invitation.used_at.is_(None),
    )
    invitation = (await db.execute(stmt)).scalar_one_or_none()

    if not invitation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Convite inválido, expirado ou já utilizado.",
        )

    biz_stmt = select(Business).where(Business.id == invitation.business_id)
    business = (await db.execute(biz_stmt)).scalar_one_or_none()

    return {
        "valid": True,
        "business_id": business.id,
        "business_name": business.name,
        "city": business.city,
        "state": business.state,
        "expires_at": invitation.expires_at.isoformat(),
    }


@router.post("/{raw_token}/accept")
async def accept_invitation(
    raw_token: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    SEGURANÇA (M12): Aceite do convite com vinculação de propriedade.
    - Marca o convite como usado (uso único).
    - Vincula o usuário autenticado como dono da empresa.
    - Eleva o papel do usuário para 'owner'.
    """
    token_hash = hash_token(raw_token)
    now = datetime.now(timezone.utc)

    stmt = select(Invitation).where(
        Invitation.token_hash == token_hash,
        Invitation.expires_at > now,
        Invitation.used_at.is_(None),
    )
    invitation = (await db.execute(stmt)).scalar_one_or_none()

    if not invitation:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Convite inválido, expirado ou já utilizado.",
        )

    biz_stmt = select(Business).where(Business.id == invitation.business_id)
    business = (await db.execute(biz_stmt)).scalar_one_or_none()

    # Consumir o convite
    invitation.used_at = now

    # Vincular proprietário
    business.owner_user_id = current_user.id
    business.is_verified = True
    current_user.role = "owner"

    await db.commit()

    return {
        "success": True,
        "message": f"Parabéns! Você agora é o proprietário verificado de {business.name}.",
        "business_id": business.id,
    }
