from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional
from uuid import UUID
import httpx
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.app.core.config import settings
from backend.app.core.database import get_db
from backend.app.core.security import get_current_active_admin
from backend.app.models.business import Business, BusinessCategory
from backend.app.models.category import Category
from backend.app.models.events import BusinessReviewLog
from backend.app.models.user import User
from backend.app.schemas.triage import TriageDecisionRequest

router = APIRouter()

# Máquina de Estados Válida para Triagem (Item M7 do Relatório)
VALID_TRANSITIONS: Dict[str, set] = {
    "pending_review": {"approved", "needs_info", "rejected"},
    "needs_info": {"pending_review", "rejected", "approved"},
    "approved": {"suspended"},
    "suspended": {"approved", "archived"},
    "rejected": set(),  # Registro rejeitado não pode ser diretamente reaprovado sem nova candidatura
    "archived": set(),
}


@router.get("/queue")
async def get_triage_queue(
    status_filter: Optional[str] = Query("pending_review"),
    city: Optional[str] = Query(None),
    source: Optional[str] = Query(None),
    limit: int = Query(50, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(get_current_active_admin),
):
    """
    Retorna a fila de triagem e análise com filtros de status, cidade e canal de origem.
    """
    stmt = (
        select(Business)
        .options(
            selectinload(Business.categories).joinedload(BusinessCategory.category)
        )
        .order_by(Business.created_at.asc())
        .limit(limit)
        .offset(offset)
    )

    if status_filter:
        stmt = stmt.where(Business.status == status_filter)
    if city:
        stmt = stmt.where(Business.city.ilike(f"%{city}%"))
    if source:
        stmt = stmt.where(Business.source == source)

    result = await db.execute(stmt)
    businesses = result.scalars().all()

    items = []
    for b in businesses:
        primary_cat = next((bc.category.name for bc in b.categories if bc.is_primary), None)
        pending_niches = [bc.category.name for bc in b.categories if bc.category and bc.category.status == "pending"]

        items.append({
            "id": b.id,
            "name": b.name,
            "slug": b.slug,
            "document_number": b.document_number,
            "document_type": b.document_type,
            "whatsapp": b.whatsapp,
            "city": b.city,
            "state": b.state,
            "neighborhood": b.neighborhood,
            "status": b.status,
            "source": b.source,
            "is_verified": b.is_verified,
            "primary_category": primary_cat,
            "pending_niches": pending_niches,
            "created_at": b.created_at,
        })

    return {
        "total": len(items),
        "results": items,
    }


@router.get("/checklist/{business_id}")
async def get_business_checklist(
    business_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(get_current_active_admin),
):
    """
    Checklist automatizado de triagem (Item M7):
    1. Consulta CNPJ no BrasilAPI com cache de 24h
    2. Detecção de duplicidade (mesmo documento ou mesmo WhatsApp)
    3. Status da geolocalização e verificação de nichos
    """
    stmt = select(Business).where(Business.id == business_id)
    business = (await db.execute(stmt)).scalar_one_or_none()

    if not business:
        raise HTTPException(status_code=404, detail="Empresa não encontrada.")

    checklist: Dict[str, Any] = {
        "business_id": business.id,
        "name": business.name,
        "document_number": business.document_number,
        "document_type": business.document_type,
        "cnpj_data": None,
        "cnpj_status": "not_checked",
        "duplicate_found": False,
        "duplicate_details": [],
        "geolocation_status": "ok" if business.location is not None else "pending_review",
        "geocode_source": business.geocode_source,
    }

    # 1. Consulta CNPJ com cache de 24h (M7)
    now = datetime.now(timezone.utc)
    is_cached = (
        business.cnpj_checked_at is not None
        and (now - business.cnpj_checked_at) < timedelta(hours=24)
        and business.cnpj_situation is not None
    )

    if is_cached:
        checklist["cnpj_status"] = "active" if "ATIVA" in business.cnpj_situation.upper() else "inactive"
        checklist["cnpj_data"] = {
            "situacao_cadastral": business.cnpj_situation,
            "cached": True,
            "last_check": business.cnpj_checked_at.isoformat(),
        }
    elif business.document_number and len(business.document_number) == 14:
        try:
            async with httpx.AsyncClient(timeout=6.0) as client:
                res = await client.get(f"{settings.BRASILAPI_BASE_URL}/cnpj/v1/{business.document_number}")
                if res.status_code == 200:
                    data = res.json()
                    situacao = data.get("descricao_situacao_cadastral", "DESCONHECIDA")
                    checklist["cnpj_data"] = {
                        "razao_social": data.get("razao_social"),
                        "nome_fantasia": data.get("nome_fantasia"),
                        "situacao_cadastral": situacao,
                        "cnae_fiscal_descricao": data.get("cnae_fiscal_descricao"),
                        "municipio": data.get("municipio"),
                        "uf": data.get("uf"),
                        "cached": False,
                    }
                    checklist["cnpj_status"] = "active" if "ATIVA" in situacao.upper() else "inactive"
                    business.cnpj_situation = situacao
                    business.cnpj_checked_at = now
                    await db.commit()
                else:
                    checklist["cnpj_status"] = "not_found"
        except Exception:
            checklist["cnpj_status"] = "api_error"

    # 2. Verificação de Duplicidade
    dup_stmt = select(Business).where(
        Business.id != business.id,
        or_(
            (Business.whatsapp == business.whatsapp),
            (
                (Business.document_number == business.document_number)
                & (Business.document_number.is_not(None))
            ),
        ),
    )
    dup_results = (await db.execute(dup_stmt)).scalars().all()
    if dup_results:
        checklist["duplicate_found"] = True
        checklist["duplicate_details"] = [
            {"id": d.id, "name": d.name, "status": d.status, "city": d.city}
            for d in dup_results
        ]

    return checklist


@router.post("/decision/{business_id}")
async def apply_triage_decision(
    business_id: UUID,
    payload: TriageDecisionRequest,
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(get_current_active_admin),
):
    """
    Aplica a decisão do analista na triagem com Máquina de Estados Estrita (Item M7):
    - Transições validadas
    - Exige resolução prévia de nichos pendentes antes da aprovação
    - reviewed_by e admin_id sempre preenchidos
    - Exige justificativa formal se o CNPJ constar inativo
    """
    stmt = select(Business).where(Business.id == business_id)
    business = (await db.execute(stmt)).scalar_one_or_none()

    if not business:
        raise HTTPException(status_code=404, detail="Empresa não encontrada.")

    old_status = business.status
    target_status_map = {
        "approve": "approved",
        "request_changes": "needs_info",
        "reject": "rejected",
        "suspend": "suspended",
    }

    new_status = target_status_map.get(payload.action)
    if not new_status:
        raise HTTPException(status_code=400, detail="Ação de triagem inválida.")

    # Validação da máquina de estados (M7)
    allowed_transitions = VALID_TRANSITIONS.get(old_status, set())
    if new_status not in allowed_transitions:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Transição de status inválida: de '{old_status}' para '{new_status}'.",
        )

    # Regras específicas de aprovação (M7 & Sec 4)
    if new_status == "approved":
        # 1. Verificar se há nichos pendentes vinculados
        pending_cats_stmt = (
            select(Category.name)
            .join(BusinessCategory, BusinessCategory.category_id == Category.id)
            .where(
                BusinessCategory.business_id == business.id,
                Category.status == "pending",
            )
        )
        pending_cats = (await db.execute(pending_cats_stmt)).scalars().all()
        if pending_cats:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Não é possível aprovar a empresa. Os seguintes nichos propostos estão pendentes de moderação: {', '.join(pending_cats)}. Aprove ou mescle-os primeiro.",
            )

        # 2. Exigir justificativa se CNPJ estiver baixado/inativo
        if business.cnpj_situation and any(x in business.cnpj_situation.upper() for x in ("BAIXADA", "INAPTA", "CANCELADA")):
            if not payload.note or len(payload.note.strip()) < 10:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="CNPJ com situação cadastral inativa/baixada. Para aprovar com override, é obrigatório registrar justificativa detalhada (mínimo 10 caracteres).",
                )

    business.status = new_status
    business.reviewed_by = current_admin.id
    business.reviewed_at = func.now()

    if payload.action == "reject":
        business.rejection_reason = payload.note
    if payload.is_verified is not None:
        business.is_verified = payload.is_verified

    # Registrar log de auditoria append-only
    log_entry = BusinessReviewLog(
        business_id=business.id,
        from_status=old_status,
        to_status=new_status,
        note=payload.note,
        admin_id=current_admin.id,
    )
    db.add(log_entry)
    await db.commit()

    return {
        "success": True,
        "business_id": business.id,
        "from_status": old_status,
        "to_status": new_status,
        "is_verified": business.is_verified,
        "reviewed_by": current_admin.id,
    }
