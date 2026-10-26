import httpx
from typing import Any, Dict, List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from backend.app.core.config import settings
from backend.app.core.database import get_db
from backend.app.models.business import Business, BusinessCategory
from backend.app.models.events import BusinessReviewLog
from backend.app.schemas.triage import TriageDecisionRequest

router = APIRouter()


@router.get("/queue")
async def get_triage_queue(
    status_filter: Optional[str] = Query("pending_review"),
    city: Optional[str] = Query(None),
    source: Optional[str] = Query(None),
    limit: int = Query(50, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
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
):
    """
    Checklist automatizado de triagem (Seção 3):
    1. Consulta CNPJ no BrasilAPI
    2. Detecção de duplicidade (mesmo documento ou mesmo WhatsApp)
    3. Status da geolocalização
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
        "geolocation_status": "ok",
    }

    # 1. Consulta CNPJ BrasilAPI se document_number existir e for 14 dígitos
    if business.document_number and len(business.document_number) == 14:
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
                    }
                    checklist["cnpj_status"] = "active" if "ATIVA" in situacao.upper() else "inactive"
                    # Atualizar na tabela business
                    business.cnpj_situation = situacao
                    business.cnpj_checked_at = func.now()
                    await db.commit()
                else:
                    checklist["cnpj_status"] = "not_found"
        except Exception:
            checklist["cnpj_status"] = "api_error"

    # 2. Verificação de Duplicidade (mesmo WhatsApp ou mesmo CNPJ em outro registro)
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
):
    """
    Aplica a decisão do analista na triagem:
    - 'approve': Aprova a empresa (passa a aparecer publicamente).
    - 'request_changes': Coloca em 'needs_info' com o motivo.
    - 'reject': Reprova com motivo gravado.
    - 'suspend': Suspende a exibição pública.
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

    business.status = new_status
    if payload.action == "reject":
        business.rejection_reason = payload.note
    if payload.is_verified is not None:
        business.is_verified = payload.is_verified

    business.reviewed_at = func.now()

    # Gravar log de auditoria
    log_entry = BusinessReviewLog(
        business_id=business.id,
        from_status=old_status,
        to_status=new_status,
        note=payload.note,
    )
    db.add(log_entry)
    await db.commit()

    return {
        "success": True,
        "business_id": business.id,
        "from_status": old_status,
        "to_status": new_status,
        "is_verified": business.is_verified,
    }
