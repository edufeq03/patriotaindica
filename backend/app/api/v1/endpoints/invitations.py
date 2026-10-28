import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select, update
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
    days_valid: int = Field(7, ge=1, le=14, description="Validade entre 1 e 14 dias (T1.7)")

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
    SEGURANÇA (T1.7 & M12): Gera convite seguro baseado em hash SHA-256.
    - Token de 32 bytes gerado criptograficamente com secrets.token_urlsafe.
    - O banco armazena APENAS o hash SHA-256.
    - Validade limitada entre 1 e 14 dias.
    - Uso único e atômico.
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
    SEGURANÇA (T1.7):
    - Consumo ATÔMICO em um único UPDATE ... WHERE used_at IS NULL RETURNING
      para impedir condições de corrida (race conditions) concorrentes.
    - Vincula o usuário autenticado como dono da empresa.
    - O selo 'is_verified' NÃO é concedido automaticamente por convite;
      permanece sob responsabilidade estrita da triagem humana.
    """
    token_hash = hash_token(raw_token)
    now = datetime.now(timezone.utc)

    # Execução atômica: consome o convite e obtém o business_id em uma única instrução SQL
    consume_stmt = (
        update(Invitation)
        .where(
            Invitation.token_hash == token_hash,
            Invitation.expires_at > now,
            Invitation.used_at.is_(None),
        )
        .values(
            used_at=now,
            used_by_user_id=current_user.id,
        )
        .returning(Invitation.id, Invitation.business_id, Invitation.phone)
    )
    result = await db.execute(consume_stmt)
    consumed = result.first()

    if not consumed:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Convite inválido, expirado ou já utilizado.",
        )

    inv_id, biz_id, inv_phone = consumed

    biz_stmt = select(Business).where(Business.id == biz_id)
    business = (await db.execute(biz_stmt)).scalar_one_or_none()
    if not business:
        await db.rollback()
        raise HTTPException(status_code=404, detail="Empresa associada ao convite não encontrada.")

    # Vincula o usuário como proprietário da empresa
    # NUNCA concede is_verified=True automaticamente (T1.7)
    business.owner_user_id = current_user.id
    if current_user.role == "user":
        current_user.role = "owner"

    await db.commit()

    return {
        "success": True,
        "message": f"Convite aceito com sucesso! Você agora é o proprietário de {business.name}.",
        "business_id": business.id,
    }
