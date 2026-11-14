import re
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Literal, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field, HttpUrl, field_validator
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.config import settings
from backend.app.core.database import get_db
from backend.app.core.security import get_current_active_admin, get_current_user
from backend.app.core.validators import BRAZIL_STATES, INSTAGRAM_REGEX
from backend.app.models.business import Business, PeerEndorsement
from backend.app.models.events import BusinessPendingChange
from backend.app.models.user import User

router = APIRouter()


class BusinessOwnerLowRiskUpdate(BaseModel):
    """
    SEGURANÇA (T1.3): Schema de atualização imediata de baixo risco.
    - extra="forbid": Impede qualquer campo de alto risco ou injeção.
    - Campos de risco (name, whatsapp, phone, website, instagram, endereço, service_mode, categorias)
      são ESTRITAMENTE proibidos aqui e devem ser submetidos via /propose-changes.
    - logo_url e banner_url devem pertencer estritamente ao diretório local /static/uploads/.
    - service_radius_km limitado a no máximo 50 km para alterações diretas.
    """
    description: Optional[str] = Field(None, max_length=2000)
    service_radius_km: Optional[int] = Field(None, ge=1, le=50)
    serves_at_location: Optional[bool] = None
    serves_at_customer: Optional[bool] = None
    serves_online: Optional[bool] = None
    show_full_address: Optional[bool] = None
    logo_url: Optional[str] = None
    banner_url: Optional[str] = None

    model_config = ConfigDict(extra="forbid")

    @field_validator("logo_url", "banner_url")
    @classmethod
    def validate_storage_path(cls, v: Optional[str]) -> Optional[str]:
        if v:
            clean = v.strip()
            if not clean.startswith("/static/uploads/"):
                raise ValueError("URLs de imagem devem apontar exclusivamente para o armazenamento interno (/static/uploads/...).")
            return clean
        return v


class BusinessOwnerProposeChanges(BaseModel):
    """
    SEGURANÇA (T1.3): Proposta de alteração de campos sensíveis/alto risco.
    - Entra em quarentena na tabela business_pending_changes.
    - A versão atualmente aprovada continua ativa e intacta no ar.
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
    service_mode: Optional[Literal["at_location", "at_customer", "both", "online"]] = None
    service_radius_km: Optional[int] = Field(None, ge=1, le=150)
    show_full_address: Optional[bool] = None
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

    @field_validator("website")
    @classmethod
    def validate_website(cls, v: Optional[str]) -> Optional[str]:
        if v:
            clean = v.strip()
            if not (clean.startswith("http://") or clean.startswith("https://")):
                clean = f"https://{clean}"
            return clean
        return v

    @field_validator("logo_url", "banner_url")
    @classmethod
    def validate_storage_path(cls, v: Optional[str]) -> Optional[str]:
        if v:
            clean = v.strip()
            if not clean.startswith("/static/uploads/"):
                raise ValueError("URLs de imagem devem apontar exclusivamente para o armazenamento interno (/static/uploads/...).")
            return clean
        return v


# Alias para retrocompatibilidade
BusinessOwnerUpdate = BusinessOwnerProposeChanges


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
            "owner_paused": getattr(b, "owner_paused", False),
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
    SEGURANÇA (T1.2):
    - Pausa ou reativa a exibição pública de uma empresa aprovada pelo próprio dono.
    - SEPARAÇÃO ESTRITA: Alterna exclusivamente a flag `owner_paused`. O campo `status` NUNCA é alterado.
    - Empresas pendentes, rejeitadas ou suspensas pela curadoria NÃO podem ser alteradas pelo dono.
    """
    stmt = select(Business).where(Business.id == business_id)
    business = (await db.execute(stmt)).scalar_one_or_none()
    if not business:
        raise HTTPException(status_code=404, detail="Empresa não encontrada.")

    if business.owner_user_id != current_user.id and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Você não tem permissão para gerenciar esta empresa.")

    if business.status != "approved":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Não é permitido alterar o status de uma empresa em '{business.status}'. Apenas empresas aprovadas podem ser pausadas pelo proprietário. Empresas em análise ou suspensas requerem moderação do administrador.",
        )

    # Alterna apenas a flag owner_paused
    business.owner_paused = not business.owner_paused
    await db.commit()
    await db.refresh(business)

    if business.owner_paused:
        msg = "Anúncio pausado com sucesso pelo proprietário. O negócio foi ocultado temporariamente das buscas públicas."
    else:
        msg = "Anúncio reativado com sucesso pelo proprietário. O negócio voltou a ser exibido nas buscas públicas."

    return {
        "success": True,
        "owner_paused": business.owner_paused,
        "status": business.status,
        "message": msg,
    }


@router.put("/{business_id}/profile")
async def update_business_profile(
    business_id: UUID,
    payload: BusinessOwnerLowRiskUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    SEGURANÇA (T1.3): Atualização direta de campos de BAIXO RISCO pelo proprietário.
    - Permite editar apenas descrição, raio (até 50km), fotos (/static/uploads/...) e métodos de atendimento.
    - Campos de risco (nome, whatsapp, endereço, website, etc.) são rejeitados com 422 e exigem /propose-changes.
    - Não altera status de curadoria nem aprovação.
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

    for key, val in changes.items():
        if hasattr(business, key):
            setattr(business, key, val)

    # Sincroniza service_mode se os booleanos de atendimento foram modificados
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

    await db.commit()
    await db.refresh(business)

    return {
        "success": True,
        "status": business.status,
        "owner_paused": business.owner_paused,
        "message": "Perfil atualizado com sucesso no seu anúncio público!",
        "business": {
            "id": str(business.id),
            "name": business.name,
            "description": business.description,
            "service_radius_km": business.service_radius_km,
            "serves_at_location": getattr(business, "serves_at_location", True),
            "serves_at_customer": getattr(business, "serves_at_customer", False),
            "serves_online": getattr(business, "serves_online", False),
            "logo_url": business.logo_url,
            "banner_url": business.banner_url,
            "status": business.status,
            "owner_paused": business.owner_paused,
            "is_verified": business.is_verified,
        },
    }


@router.post("/{business_id}/propose-changes")
async def propose_business_changes(
    business_id: UUID,
    payload: BusinessOwnerProposeChanges,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    SEGURANÇA (T1.3 & H3):
    - O proprietário propõe alterações em dados sensíveis (nome, WhatsApp, endereço, site, etc.).
    - A versão APROVADA atualmente no ar continua publicada e intacta.
    - Teto estrito de 3 alterações pendentes por empresa para evitar sobrecarga na fila de moderação.
    - As alterações entram em quarentena na tabela 'business_pending_changes'.
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

    # Checa teto de 3 solicitações pendentes abertas
    count_stmt = select(func.count(BusinessPendingChange.id)).where(
        BusinessPendingChange.business_id == business.id,
        BusinessPendingChange.status == "pending_review",
    )
    pending_count = (await db.execute(count_stmt)).scalar() or 0
    if pending_count >= 3:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Limite de 3 alterações pendentes atingido para esta empresa. Aguarde a moderação da equipe antes de submeter novas mudanças.",
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
        "message": "Alterações enviadas com sucesso! Nossa curadoria analisará os novos dados antes de aplicá-los ao anúncio.",
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
    Decisão do administrador sobre alterações propostas pelo dono (T1.3):
    - 'approve': Aplica as mudanças validadas na tabela 'businesses'.
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


# ==============================================================================
# SPRINT 7: REDE DE NEGÓCIOS CONFIÁVEIS, DISPONIBILIDADE E INDICAÇÕES MÚTUAS
# ==============================================================================

class AvailabilityUpdate(BaseModel):
    """
    T7.1: Selo 'Disponível Agora' / Plantão Imediato
    - Permite ativar atendimento urgente/imediato por 1 a 24 horas.
    - 0 desativa a disponibilidade imediata.
    """
    hours: int = Field(..., ge=0, le=24, description="0 para desativar, 1 a 24 horas para definir plantão imediato")


@router.post("/{business_id}/availability")
async def update_business_availability(
    business_id: UUID,
    payload: AvailabilityUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Ativa ou desativa o selo 'Disponível Agora' da empresa para serviços emergenciais.
    """
    stmt = select(Business).where(Business.id == business_id)
    business = (await db.execute(stmt)).scalar_one_or_none()
    if not business:
        raise HTTPException(status_code=404, detail="Empresa não encontrada.")

    if business.owner_user_id != current_user.id and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Acesso não autorizado.")

    if business.status != "approved":
        raise HTTPException(status_code=400, detail="Apenas empresas aprovadas podem ativar o selo 'Disponível Agora'.")

    now = datetime.now(timezone.utc)
    if payload.hours == 0:
        business.availability_until = None
        await db.commit()
        return {
            "success": True,
            "is_available_now": False,
            "availability_until": None,
            "message": "Disponibilidade imediata desativada.",
        }

    business.availability_until = now + timedelta(hours=payload.hours)
    await db.commit()
    return {
        "success": True,
        "is_available_now": True,
        "availability_until": business.availability_until.isoformat(),
        "remaining_hours": payload.hours,
        "message": f"Selo 'Disponível Agora' ativado com sucesso pelas próximas {payload.hours}h.",
    }


class PeerEndorsementCreate(BaseModel):
    """
    T7.2: Indicação Mútua Entre Pares da Rede de Confiança
    - Permite a uma empresa parceira recomendar outro membro aprovado da rede.
    """
    target_business_id: UUID
    relationship_type: Literal["client", "partner", "peer", "supplier"] = "peer"
    testimonial: Optional[str] = Field(None, max_length=500, description="Depoimento ou motivo da recomendação de confiança")


@router.post("/{business_id}/endorsements")
async def create_or_update_endorsement(
    business_id: UUID,
    payload: PeerEndorsementCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Cria ou atualiza uma recomendação de confiança para outra empresa parceira da rede.
    """
    if not settings.FEATURE_NETWORK:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Módulo de rede de recomendações entre empresas congelado temporariamente.",
        )

    if business_id == payload.target_business_id:
        raise HTTPException(status_code=400, detail="Uma empresa não pode recomendar a si própria.")

    # 1. Validar que a empresa indicadora pertence ao usuário e está aprovada
    biz_stmt = select(Business).where(Business.id == business_id)
    endorsing_biz = (await db.execute(biz_stmt)).scalar_one_or_none()
    if not endorsing_biz:
        raise HTTPException(status_code=404, detail="Empresa de origem não encontrada.")

    if endorsing_biz.owner_user_id != current_user.id and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Acesso não autorizado a esta empresa.")

    if endorsing_biz.status != "approved":
        raise HTTPException(status_code=400, detail="Apenas empresas aprovadas podem conceder recomendações na rede.")

    # 2. Validar que a empresa indicada existe e está aprovada
    target_stmt = select(Business).where(Business.id == payload.target_business_id)
    target_biz = (await db.execute(target_stmt)).scalar_one_or_none()
    if not target_biz:
        raise HTTPException(status_code=404, detail="Empresa indicada não encontrada.")

    if target_biz.status != "approved":
        raise HTTPException(status_code=400, detail="Apenas empresas aprovadas podem receber recomendações na rede.")

    # 3. Buscar ou criar o endosso
    endorsement_stmt = select(PeerEndorsement).where(
        PeerEndorsement.endorsing_business_id == business_id,
        PeerEndorsement.endorsed_business_id == payload.target_business_id,
    )
    endorsement = (await db.execute(endorsement_stmt)).scalar_one_or_none()

    now = datetime.now(timezone.utc)
    if endorsement:
        endorsement.relationship_type = payload.relationship_type
        endorsement.testimonial = payload.testimonial
        endorsement.is_public = True
        endorsement.updated_at = now
    else:
        endorsement = PeerEndorsement(
            endorsing_business_id=business_id,
            endorsed_business_id=payload.target_business_id,
            relationship_type=payload.relationship_type,
            testimonial=payload.testimonial,
            is_public=True,
            created_at=now,
            updated_at=now,
        )
        db.add(endorsement)

    await db.flush()

    # 4. Atualizar o contador de endossos da empresa indicada
    count_stmt = select(func.count(PeerEndorsement.id)).where(
        PeerEndorsement.endorsed_business_id == payload.target_business_id,
        PeerEndorsement.is_public.is_(True),
    )
    total_endorsements = (await db.execute(count_stmt)).scalar() or 0
    target_biz.endorsements_count = total_endorsements

    await db.commit()

    return {
        "success": True,
        "endorsement_id": str(endorsement.id),
        "endorsing_business_name": endorsing_biz.name,
        "endorsed_business_name": target_biz.name,
        "relationship_type": endorsement.relationship_type,
        "testimonial": endorsement.testimonial,
        "total_endorsements_target": target_biz.endorsements_count,
        "message": f"Recomendação de confiança registrada para {target_biz.name}!",
    }


@router.delete("/{business_id}/endorsements/{target_business_id}")
async def remove_endorsement(
    business_id: UUID,
    target_business_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Remove uma recomendação concedida a outra empresa.
    """
    biz_stmt = select(Business).where(Business.id == business_id)
    endorsing_biz = (await db.execute(biz_stmt)).scalar_one_or_none()
    if not endorsing_biz:
        raise HTTPException(status_code=404, detail="Empresa de origem não encontrada.")

    if endorsing_biz.owner_user_id != current_user.id and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Acesso não autorizado.")

    endorsement_stmt = select(PeerEndorsement).where(
        PeerEndorsement.endorsing_business_id == business_id,
        PeerEndorsement.endorsed_business_id == target_business_id,
    )
    endorsement = (await db.execute(endorsement_stmt)).scalar_one_or_none()
    if not endorsement:
        raise HTTPException(status_code=404, detail="Recomendação não encontrada.")

    await db.delete(endorsement)
    await db.flush()

    # Recalcular contador
    target_stmt = select(Business).where(Business.id == target_business_id)
    target_biz = (await db.execute(target_stmt)).scalar_one_or_none()
    if target_biz:
        count_stmt = select(func.count(PeerEndorsement.id)).where(
            PeerEndorsement.endorsed_business_id == target_business_id,
            PeerEndorsement.is_public.is_(True),
        )
        target_biz.endorsements_count = (await db.execute(count_stmt)).scalar() or 0

    await db.commit()
    return {"success": True, "message": "Recomendação removida com sucesso."}

