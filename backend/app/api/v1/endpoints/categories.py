from typing import List, Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from backend.app.core.database import get_db
from backend.app.models.business import Business, BusinessCategory
from backend.app.models.category import Category
from backend.app.schemas.category import CategoryOut

router = APIRouter()


@router.get("", response_model=List[CategoryOut])
async def list_categories(
    kind: Optional[str] = Query(None, description="'service', 'product', ou 'both'"),
    db: AsyncSession = Depends(get_db),
):
    """
    Lista todas as categorias cadastradas para o catálogo e filtros da home.
    """
    stmt = select(Category).order_by(Category.display_order.asc(), Category.name.asc())

    if kind and kind in ("service", "product"):
        stmt = stmt.where((Category.kind == kind) | (Category.kind == "both"))

    result = await db.execute(stmt)
    categories = result.scalars().all()
    return categories
