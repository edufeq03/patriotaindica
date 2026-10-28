from typing import Any, Dict, List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.database import get_db
from backend.app.core.rate_limit import check_rate_limit, get_client_ip
from backend.app.models.city import City, CityWaitlist

router = APIRouter()


class WaitlistCreate(BaseModel):
    contact: str = Field(..., min_length=5, max_length=100, description="E-mail ou WhatsApp do interessado")
    is_business: bool = Field(False, description="Se é prestador/empresa interessada em se cadastrar")


@router.get("", response_model=Dict[str, List[Dict[str, Any]]])
async def list_cities(
    db: AsyncSession = Depends(get_db),
):
    """
    Retorna catálogo de cidades ativas e em expansão (Cold Start / Rollout T3.4).
    """
    stmt = select(City).order_by(City.status.asc(), City.interested_count.desc(), City.name.asc())
    result = await db.execute(stmt)
    cities = result.scalars().all()

    active_cities = []
    soon_cities = []

    for c in cities:
        item = {
            "id": str(c.id),
            "name": c.name,
            "state": c.state,
            "slug": c.slug,
            "status": c.status,
            "interested_count": c.interested_count,
        }
        if c.status == "active":
            active_cities.append(item)
        else:
            soon_cities.append(item)

    return {
        "active": active_cities,
        "soon": soon_cities,
    }


@router.post("/{city_id}/waitlist", status_code=status.HTTP_201_CREATED)
async def join_city_waitlist(
    city_id: UUID,
    payload: WaitlistCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """
    Cadastra interesse na lista de espera de cidades em expansão (T3.4).
    """
    client_ip = get_client_ip(request)
    await check_rate_limit(
        key=f"ratelimit:waitlist:{client_ip}",
        limit=5,
        window_seconds=3600,
        error_msg="Muitas inscrições na lista de espera a partir deste IP. Aguarde uma hora.",
    )

    stmt = select(City).where(City.id == city_id)
    city = (await db.execute(stmt)).scalar_one_or_none()

    if not city:
        raise HTTPException(status_code=404, detail="Cidade não encontrada.")

    # Registra na fila de espera
    entry = CityWaitlist(
        city_id=city.id,
        contact=payload.contact.strip(),
        is_business=payload.is_business,
    )
    db.add(entry)

    # Incrementa contador de interessados
    city.interested_count += 1
    await db.commit()

    return {
        "success": True,
        "message": f"Inscrição confirmada na lista de espera de {city.name} - {city.state}!",
        "interested_count": city.interested_count,
    }
