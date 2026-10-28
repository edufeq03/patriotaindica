import re
import secrets
import unicodedata
from typing import Any, Dict, List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.database import get_db
from backend.app.core.rate_limit import check_rate_limit, get_client_ip
from backend.app.core.security import get_current_active_admin
from backend.app.models.business import BusinessCategory
from backend.app.models.category import Category, CategoryAlias
from backend.app.models.user import User
from backend.app.schemas.category import (
    CategoryAdminCreate,
    CategoryModerationAction,
    CategoryOut,
    CategoryProposalCreate,
    CategorySuggestOut,
)

router = APIRouter()


def slugify_category(text: str) -> str:
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("utf-8")
    text = re.sub(r"[^\w\s-]", "", text).strip().lower()
    return re.sub(r"[-\s]+", "-", text)


@router.get("", response_model=List[CategoryOut])
async def list_categories(
    kind: Optional[str] = Query(None, description="'service', 'product', ou 'both'"),
    include_all: bool = Query(False, description="Se True, inclui todas as categorias exceto arquivadas"),
    db: AsyncSession = Depends(get_db),
):
    """
    Lista categorias para o catálogo público e filtros da home.
    Por padrão retorna apenas status='approved'.
    Com include_all=True retorna todas que não estão 'archived'.
    """
    stmt = select(Category).order_by(Category.display_order.asc(), Category.name.asc())

    if include_all:
        stmt = stmt.where(Category.status != "archived")
    else:
        stmt = stmt.where(Category.status == "approved")

    if kind and kind in ("service", "product"):
        stmt = stmt.where((Category.kind == kind) | (Category.kind == "both"))

    result = await db.execute(stmt)
    return result.scalars().all()


@router.get("/suggest", response_model=List[CategorySuggestOut])
async def suggest_categories(
    q: str = Query(..., min_length=2, max_length=60, description="Termo digitado pelo usuário"),
    db: AsyncSession = Depends(get_db),
):
    """
    Autocomplete inteligente para seleção de nichos:
    1. Busca categorias aprovadas por nome
    2. Busca sinônimos/aliases cadastrados
    """
    clean_q = q.strip()

    # 1. Buscar categorias aprovadas
    cat_stmt = (
        select(Category)
        .where(
            Category.status == "approved",
            Category.name.ilike(f"%{clean_q}%"),
        )
        .limit(10)
    )
    categories = (await db.execute(cat_stmt)).scalars().all()

    suggestions: List[CategorySuggestOut] = [
        CategorySuggestOut(
            id=c.id,
            name=c.name,
            slug=c.slug,
            kind=c.kind,
            is_alias=False,
        )
        for c in categories
    ]

    # 2. Buscar em aliases se houver espaço
    if len(suggestions) < 10:
        alias_stmt = (
            select(CategoryAlias, Category)
            .join(Category, Category.id == CategoryAlias.category_id)
            .where(
                Category.status == "approved",
                CategoryAlias.alias_name.ilike(f"%{clean_q}%"),
            )
            .limit(10 - len(suggestions))
        )
        aliases = (await db.execute(alias_stmt)).all()
        for alias, parent_cat in aliases:
            # Evitar duplicar a categoria canônica
            if not any(s.id == parent_cat.id for s in suggestions):
                suggestions.append(
                    CategorySuggestOut(
                        id=parent_cat.id,
                        name=alias.alias_name,
                        slug=parent_cat.slug,
                        kind=parent_cat.kind,
                        is_alias=True,
                        canonical_name=parent_cat.name,
                    )
                )

    return suggestions


@router.post("/propose", status_code=status.HTTP_201_CREATED)
async def propose_new_category(
    payload: CategoryProposalCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """
    Canal de Nichos Dinâmicos (Sec. 4 do Relatório):
    - Permite propor novos nichos de cauda longa ('Cuidador de Iguanas Selvagens')
    - Nasce estritamente como status='pending'
    - Não aparece publicamente até ser aprovado pela curadoria
    """
    client_ip = get_client_ip(request)
    await check_rate_limit(
        key=f"ratelimit:propose_category:{client_ip}",
        limit=5,
        window_seconds=86400,
        error_msg="Limite diário de propostas de novos nichos atingido.",
    )

    base_slug = slugify_category(payload.name)
    slug = base_slug
    attempts = 0
    while attempts < 5:
        stmt = select(Category.id).where(Category.slug == slug)
        exists = (await db.execute(stmt)).scalar_one_or_none()
        if not exists:
            break
        slug = f"{base_slug}-{secrets.token_hex(2)}"
        attempts += 1

    new_cat = Category(
        name=payload.name,
        slug=slug,
        kind=payload.kind,
        parent_id=payload.parent_id,
        status="pending",
        icon_name="sparkles",
        proposed_by_business_id=payload.business_id,
    )
    db.add(new_cat)
    await db.commit()
    await db.refresh(new_cat)

    return {
        "success": True,
        "message": "Nicho proposto enviado para curadoria. Será analisado junto à candidatura.",
        "category_id": new_cat.id,
        "name": new_cat.name,
        "status": "pending",
    }


@router.post("/{category_id}/moderate")
async def moderate_category(
    category_id: UUID,
    payload: CategoryModerationAction,
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(get_current_active_admin),
):
    """
    Moderação administrativa de nicho proposto (Sec. 4):
    - 'approve': Aprova como novo nicho público
    - 'merge': Mescla em nicho existente (criando alias)
    - 'reject': Rejeita a proposta
    """
    stmt = select(Category).where(Category.id == category_id)
    category = (await db.execute(stmt)).scalar_one_or_none()

    if not category:
        raise HTTPException(status_code=404, detail="Categoria não encontrada.")

    if payload.action == "approve":
        category.status = "approved"
        if payload.adjusted_name:
            category.name = payload.adjusted_name.strip()
            category.slug = slugify_category(category.name)
        if payload.icon_name:
            category.icon_name = payload.icon_name
        await db.commit()
        return {"success": True, "action": "approved", "category_id": category.id, "name": category.name}

    elif payload.action == "merge":
        if not payload.merged_into_category_id:
            raise HTTPException(status_code=400, detail="merged_into_category_id obrigatório para mesclagem.")

        target_stmt = select(Category).where(Category.id == payload.merged_into_category_id)
        target_category = (await db.execute(target_stmt)).scalar_one_or_none()
        if not target_category:
            raise HTTPException(status_code=404, detail="Categoria de destino não encontrada.")

        # Criar alias com o nome do nicho mesclado
        alias = CategoryAlias(
            category_id=target_category.id,
            alias_name=category.name,
        )
        db.add(alias)

        # Reatribuir empresas vinculadas ao nicho original para o nicho de destino
        biz_cats_stmt = select(BusinessCategory).where(BusinessCategory.category_id == category.id)
        biz_cats = (await db.execute(biz_cats_stmt)).scalars().all()
        for bc in biz_cats:
            bc.category_id = target_category.id

        # Remover categoria temporária
        await db.delete(category)
        await db.commit()

        return {
            "success": True,
            "action": "merged",
            "merged_into": target_category.name,
            "created_alias": alias.alias_name,
        }

    elif payload.action == "reject":
        category.status = "rejected"
        await db.commit()
        return {"success": True, "action": "rejected", "category_id": category.id}

    raise HTTPException(status_code=400, detail="Ação inválida.")


@router.post("", response_model=CategoryOut, status_code=status.HTTP_201_CREATED)
async def create_category(
    payload: CategoryAdminCreate,
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(get_current_active_admin),
):
    """
    Criação direta de categoria pelo Administrador no PostgreSQL com status 'approved'.
    """
    clean_name = payload.name.strip()
    base_slug = slugify_category(clean_name)
    slug = base_slug
    attempts = 0
    while attempts < 5:
        stmt = select(Category.id).where(Category.slug == slug)
        exists = (await db.execute(stmt)).scalar_one_or_none()
        if not exists:
            break
        slug = f"{base_slug}-{secrets.token_hex(2)}"
        attempts += 1

    new_cat = Category(
        name=clean_name,
        slug=slug,
        kind=payload.kind,
        icon_name=payload.icon_name or "wrench",
        display_order=payload.display_order or 0,
        status="approved",
    )
    db.add(new_cat)
    await db.commit()
    await db.refresh(new_cat)
    return new_cat


@router.delete("/{category_id}", status_code=status.HTTP_200_OK)
async def delete_category(
    category_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(get_current_active_admin),
):
    """
    Exclusão / Desativação de categoria pelo Administrador.
    Se houver empresas vinculadas, desativa marcando status='archived' para manter integridade.
    Se não houver empresas vinculadas, remove fisicamente do banco.
    """
    stmt = select(Category).where(Category.id == category_id)
    category = (await db.execute(stmt)).scalar_one_or_none()
    if not category:
        raise HTTPException(status_code=404, detail="Categoria não encontrada.")

    # Verificar vínculos com empresas
    biz_stmt = select(func.count()).select_from(BusinessCategory).where(BusinessCategory.category_id == category_id)
    linked_count = (await db.execute(biz_stmt)).scalar() or 0

    if linked_count > 0:
        category.status = "archived"
        await db.commit()
        return {
            "success": True,
            "message": f"Categoria desativada (arquivada), pois está vinculada a {linked_count} empresa(s).",
            "archived": True,
        }
    else:
        await db.delete(category)
        await db.commit()
        return {
            "success": True,
            "message": "Categoria removida com sucesso.",
            "archived": False,
        }

