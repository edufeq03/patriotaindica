from datetime import datetime, timezone
from typing import Any, Dict, List, Literal, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.database import get_db
from backend.app.core.security import get_current_active_admin, get_current_user
from backend.app.core.validators import BRAZIL_STATES, INSTAGRAM_REGEX
from backend.app.models.business import Business
from backend.app.models.events import BusinessPendingChange
from backend.app.models.user import User

router = APIRouter()


class BusinessOwnerUpdate(BaseModel):
    """
    SEGURANÇA (H3): Schema de atualização proposto pelo dono da empresa.
    - extra="forbid": Impede injeção de campos não autorizados.
    - Status, is_verified, owner_user_id, document_* NUNCA podem ser alterados aqui.
    """
    name: Optional[str] = Field(None, min_length=2, max_length=150)
    description: Optional[str] = Field(None, max_length=2000)
    whatsapp: Optional[str] = Field(None, min_length=8, max_length=20)
    phone: Optional[str] = Field(None, max_length=20)
    website: Optional[str] = Field(None, max_length=255)
    instagram: Optional[str] = Field(None, max_length=100)
    street: Optional[str] = Field(None, max_length=150)
    number: Optional[str] = Field(None, max_length=30)
    neighborhood: Optional[str] = Field(None, max_length=100)
    city: Optional[str] = Field(None, max_length=100)
    state: Optional[str] = Field(None, max_length=2)
    postal_code: Optional[str] = Field(None, max_length=10)
    show_full_address: Optional[bool] = None
    service_mode: Optional[Literal["at_location", "at_customer", "both", "online"]] = None
    service_radius_km: Optional[int] = Field(None, ge=1, le=500)
    serves_at_location: Optional[bool] = None
    serves_at_customer: Optional[bool] = None
    serves_online: Optional[bool] = None
    logo_url: Optional[str] = None
    banner_url: Optional[str] = None

    model_config = ConfigDict(extra="forbid")

    @field_validator("state")
    @classmethod
    def validate_state(cls, v: Optional[str]) -> Optional[str]:
        if v:
            uf = v.upper().strip()
            if uf not in BRAZIL_STATES:
                raise ValueError("Estado (UF) inválido.")
            return uf
        return v

    @field_validator("instagram")
    @classmethod
    def validate_instagram(cls, v: Optional[str]) -> Optional[str]:
        if v:
            clean = v.strip().lstrip("@")
            if clean and not INSTAGRAM_REGEX.match(clean):
                raise ValueError("Usuário do Instagram inválido.")
            return clean
        return v


@router.get("/my-businesses")
async def get_my_businesses(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Retorna os negócios pertencentes ao usuário autenticado (ou todos os negócios, se for admin).
    """
    if current_user.role == "admin":
        stmt = select(Business).order_by(Business.created_at.desc())
    else:
        stmt = select(Business).where(Business.owner_user_id == current_user.id).order_by(Business.created_at.desc())

    result = await db.execute(stmt)
    businesses = result.scalars().all()

    return [
        {
            "id": str(b.id),
            "name": b.name,
            "slug": b.slug,
            "description": b.description,
            "listing_type": b.listing_type,
            "service_mode": b.service_mode,
            "service_radius_km": b.service_radius_km,
            "serves_at_location": getattr(b, "serves_at_location", True),
            "serves_at_customer": getattr(b, "serves_at_customer", False),
            "serves_online": getattr(b, "serves_online", False),
            "referral_code": getattr(b, "referral_code", None) or f"PAT-{str(b.id).replace('-', '')[:6].upper()}",
            "whatsapp": b.whatsapp,
            "phone": b.phone,
            "website": b.website,
            "instagram": b.instagram,
            "street": b.street,
            "number": b.number,
            "neighborhood": b.neighborhood,
            "city": b.city,
            "state": b.state,
            "postal_code": b.postal_code,
            "show_full_address": b.show_full_address,
            "logo_url": b.logo_url,
            "banner_url": b.banner_url,
            "status": b.status,
            "is_verified": b.is_verified,
            "created_at": b.created_at.isoformat() if b.created_at else None,
        }
        for b in businesses
    ]


@router.post("/{business_id}/toggle-pause")
async def toggle_business_pause(
    business_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Pausa ou reativa um anúncio aprovado pelo dono do negócio.
    """
    stmt = select(Business).where(Business.id == business_id)
    business = (await db.execute(stmt)).scalar_one_or_none()
    if not business:
        raise HTTPException(status_code=404, detail="Empresa não encontrada.")

    if business.owner_user_id != current_user.id and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Você não tem permissão para gerenciar esta empresa.")

    if business.status == "approved":
        business.status = "suspended"
        msg = "Anúncio pausado com sucesso. Ele foi ocultado temporariamente das buscas públicas."
    elif business.status in ("suspended", "pending_review"):
        business.status = "approved"
        msg = "Anúncio ativado com sucesso! Já está visível novamente nas buscas públicas."
    else:
        raise HTTPException(
            status_code=400,
            detail=f"Não é possível alterar um anúncio em status '{business.status}'.",
        )

    await db.commit()
    await db.refresh(business)
    return {
        "success": True,
        "status": business.status,
        "message": msg,
    }


@router.put("/{business_id}/profile")
async def update_business_profile(
    business_id: UUID,
    payload: BusinessOwnerUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Atualiza dados do perfil da empresa diretamente pelo proprietário.
    Campos como descrição, fotos, instagram, website são atualizados de imediato.
    Se alterar WhatsApp ou Localização, o status volta para 'pending_review' para revalidação de segurança.
    """
    stmt = select(Business).where(Business.id == business_id)
    business = (await db.execute(stmt)).scalar_one_or_none()
    if not business:
        raise HTTPException(status_code=404, detail="Empresa não encontrada.")

    if business.owner_user_id != current_user.id and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Você não tem permissão para gerenciar esta empresa.")

    changes = payload.model_dump(exclude_unset=True)
    if not changes:
        raise HTTPException(status_code=400, detail="Nenhum dado informado para atualização.")

    sensitive_keys = {"whatsapp", "neighborhood", "city", "street", "number"}
    reopened = False

    for key, val in changes.items():
        if hasattr(business, key):
            setattr(business, key, val)
        if key in sensitive_keys and val:
            reopened = True

    # Sincronizar service_mode a partir dos booleanos se foram modificados
    if any(k in changes for k in ("serves_at_location", "serves_at_customer", "serves_online")):
        cust = bool(business.serves_at_customer)
        loc = bool(business.serves_at_location)
        onl = bool(business.serves_online)
        if cust and loc:
            business.service_mode = "both"
        elif cust:
            business.service_mode = "at_customer"
        elif onl and not loc:
            business.service_mode = "online"
        else:
            business.service_mode = "at_location"

    if reopened and business.status == "approved":
        business.status = "pending_review"

    await db.commit()
    await db.refresh(business)

    return {
        "success": True,
        "reopened_triage": reopened,
        "status": business.status,
        "message": (
            "Perfil atualizado! Por conter alteração de WhatsApp ou Endereço, o status reabriu para 'Em Análise' na triagem por segurança."
            if reopened
            else "Perfil atualizado com sucesso no seu anúncio público!"
        ),
        "business": {
            "id": str(business.id),
            "name": business.name,
            "description": business.description,
            "whatsapp": business.whatsapp,
            "phone": business.phone,
            "website": business.website,
            "instagram": business.instagram,
            "neighborhood": business.neighborhood,
            "city": business.city,
            "state": business.state,
            "service_mode": business.service_mode,
            "service_radius_km": business.service_radius_km,
            "serves_at_location": getattr(business, "serves_at_location", True),
            "serves_at_customer": getattr(business, "serves_at_customer", False),
            "serves_online": getattr(business, "serves_online", False),
            "logo_url": business.logo_url,
            "banner_url": business.banner_url,
            "status": business.status,
            "is_verified": business.is_verified,
        },
    }


@router.post("/{business_id}/propose-changes")
async def propose_business_changes(
    business_id: UUID,
    payload: BusinessOwnerUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    SEGURANÇA (H3): O proprietário propõe alterações nos dados da empresa.
    A versão APROVADA atualmente no ar continua publicada e intacta.
    As alterações entram em quarentena em 'business_pending_changes' para curadoria do admin.
    """
    stmt = select(Business).where(Business.id == business_id)
    business = (await db.execute(stmt)).scalar_one_or_none()

    if not business:
        raise HTTPException(status_code=404, detail="Empresa não encontrada.")

    if business.owner_user_id != current_user.id and current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Você não possui permissão para gerenciar esta empresa.",
        )

    changes_dict = payload.model_dump(exclude_unset=True)
    if not changes_dict:
        raise HTTPException(status_code=400, detail="Nenhuma alteração informada.")

    pending_change = BusinessPendingChange(
        business_id=business.id,
        proposed_by_user_id=current_user.id,
        changes=changes_dict,
        status="pending_review",
    )
    db.add(pending_change)
    await db.commit()
    await db.refresh(pending_change)

    return {
        "success": True,
        "message": "Alterações enviadas com sucesso! Nossa curadoria analisará os novos dados em até 24h.",
        "pending_change_id": pending_change.id,
        "changes": changes_dict,
    }


@router.get("/{business_id}/pending-changes")
async def get_pending_changes(
    business_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Lista alterações pendentes de uma empresa.
    """
    stmt = select(Business).where(Business.id == business_id)
    business = (await db.execute(stmt)).scalar_one_or_none()
    if not business:
        raise HTTPException(status_code=404, detail="Empresa não encontrada.")

    if business.owner_user_id != current_user.id and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Acesso não autorizado.")

    changes_stmt = (
        select(BusinessPendingChange)
        .where(BusinessPendingChange.business_id == business_id)
        .order_by(BusinessPendingChange.created_at.desc())
    )
    changes = (await db.execute(changes_stmt)).scalars().all()
    return changes


@router.post("/pending-changes/{change_id}/decide")
async def decide_pending_change(
    change_id: UUID,
    action: Literal["approve", "reject"],
    rejection_reason: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(get_current_active_admin),
):
    """
    Decisão do administrador sobre alterações propostas pelo dono (H3):
    - 'approve': Aplica as mudanças diretamente na tabela 'businesses'.
    - 'reject': Rejeita e mantém a versão original no ar.
    """
    stmt = select(BusinessPendingChange).where(BusinessPendingChange.id == change_id)
    pending = (await db.execute(stmt)).scalar_one_or_none()

    if not pending:
        raise HTTPException(status_code=404, detail="Solicitação de alteração não encontrada.")

    if pending.status != "pending_review":
        raise HTTPException(status_code=400, detail="Esta solicitação já foi decidida anteriormente.")

    biz_stmt = select(Business).where(Business.id == pending.business_id)
    business = (await db.execute(biz_stmt)).scalar_one_or_none()

    now = datetime.now(timezone.utc)
    pending.reviewed_by = current_admin.id
    pending.reviewed_at = now

    if action == "approve":
        pending.status = "approved"
        for field, value in pending.changes.items():
            if hasattr(business, field):
                setattr(business, field, value)
        await db.commit()
        return {"success": True, "action": "approved", "business_id": business.id}

    elif action == "reject":
        pending.status = "rejected"
        pending.rejection_reason = rejection_reason or "Alterações não atendem aos critérios de qualidade."
        await db.commit()
        return {"success": True, "action": "rejected", "rejection_reason": pending.rejection_reason}
