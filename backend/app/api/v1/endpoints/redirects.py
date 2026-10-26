import urllib.parse
from uuid import UUID
from fastapi import APIRouter, Depends, Header, HTTPException, Request, Response
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from backend.app.core.database import get_db
from backend.app.models.business import Business
from backend.app.models.events import ContactEvent

router = APIRouter()


@router.get("/{event_type}/{business_id}")
async def redirect_contact_event(
    event_type: str,
    business_id: UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user_agent: str = Header(None),
    referer: str = Header(None),
):
    """
    Rastreamento de métricas e conversão de cliques:
    1. Registra o evento de contato no banco de dados (contact_events).
    2. Redireciona com segurança para wa.me, telefone ou site da empresa.
    """
    if event_type not in ("whatsapp", "phone", "website"):
        raise HTTPException(status_code=400, detail="Tipo de contato inválido.")

    # Buscar empresa aprovada
    stmt = select(Business).where(
        Business.id == business_id,
        Business.status == "approved",
    )
    result = await db.execute(stmt)
    business = result.scalar_one_or_none()

    if not business:
        raise HTTPException(status_code=404, detail="Empresa não encontrada ou não ativa.")

    # 1. Gravar métrica em contact_events
    event = ContactEvent(
        business_id=business.id,
        event_type=event_type,
        city=business.city,
        referrer=referer,
        user_agent=user_agent,
    )
    db.add(event)
    await db.commit()

    # 2. Construir destino do redirecionamento
    destination_url = ""
    if event_type == "whatsapp":
        # Limpar caracteres não numéricos
        clean_number = "".join(filter(str.isdigit, business.whatsapp))
        if not clean_number.startswith("55") and len(clean_number) in (10, 11):
            clean_number = f"55{clean_number}"

        default_msg = f"Olá! Vi seu anúncio no Guia Local e gostaria de solicitar informações/orçamento sobre {business.name}."
        encoded_msg = urllib.parse.quote(default_msg)
        destination_url = f"https://wa.me/{clean_number}?text={encoded_msg}"

    elif event_type == "phone":
        clean_phone = "".join(filter(str.isdigit, business.phone or business.whatsapp))
        destination_url = f"tel:{clean_phone}"

    elif event_type == "website":
        if not business.website:
            raise HTTPException(status_code=400, detail="Empresa não possui site cadastrado.")
        destination_url = business.website
        if not destination_url.startswith(("http://", "https://")):
            destination_url = f"https://{destination_url}"

    # Redirecionamento 307 Temporary Redirect
    return RedirectResponse(url=destination_url, status_code=307)
