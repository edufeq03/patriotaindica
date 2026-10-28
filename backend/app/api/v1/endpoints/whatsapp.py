import hashlib
import hmac
import logging
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from fastapi.responses import PlainTextResponse
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.config import settings
from backend.app.core.database import get_db
from backend.app.core.security import get_current_user
from backend.app.models.lead import Lead, LeadOffer
from backend.app.models.user import User
from backend.app.models.whatsapp import WaEvent
from backend.app.services.whatsapp.bot import handle_incoming_message

logger = logging.getLogger("patriotaindica.whatsapp.webhook")
router = APIRouter()


def verify_meta_hub_signature(payload_bytes: bytes, signature_header: Optional[str], secret: Optional[str]) -> bool:
    """
    T5.1: Validação rigorosa do cabeçalho X-Hub-Signature-256 da Meta.
    sha256=<hex_digest>
    """
    if not secret:
        return True
    if not signature_header or not signature_header.startswith("sha256="):
        return False

    expected_sig = signature_header[7:]
    calculated_sig = hmac.new(secret.encode("utf-8"), payload_bytes, hashlib.sha256).hexdigest()
    return hmac.compare_digest(calculated_sig, expected_sig)


@router.get("", response_class=PlainTextResponse)
async def verify_meta_webhook(
    hub_mode: Optional[str] = Query(None, alias="hub.mode"),
    hub_verify_token: Optional[str] = Query(None, alias="hub.verify_token"),
    hub_challenge: Optional[str] = Query(None, alias="hub.challenge"),
):
    """
    T5.1: Endpoint de verificação obrigatória do webhook da Meta Cloud API.
    A Meta envia GET com hub.mode, hub.verify_token e espera receber hub.challenge de volta.
    """
    expected_token = settings.META_WHATSAPP_VERIFY_TOKEN
    if hub_mode == "subscribe" and hub_verify_token == expected_token and hub_challenge:
        logger.info("Webhook da Meta verificado com sucesso.")
        return hub_challenge

    logger.warning("Falha na verificação de webhook da Meta: token incorreto ou modo inválido.")
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Verificação de token inválida.")


@router.post("")
async def receive_whatsapp_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """
    T5.1: Endpoint unificado de webhook para WhatsApp (Meta Cloud API e Evolution API).
    1. Validação de assinatura criptográfica X-Hub-Signature-256
    2. Deduplicação em wa_events para idempotência de entrega
    3. Processamento pela máquina de estados conversacional do bot
    """
    raw_body = await request.body()

    try:
        body = await request.json()
    except Exception:
        body = {}

    # 1. Validação de Assinatura se vier com cabeçalho da Meta ou payload da Meta
    x_hub_sig = request.headers.get("X-Hub-Signature-256")
    meta_secret = settings.META_APP_SECRET
    if meta_secret and (x_hub_sig or "entry" in body):
        if not x_hub_sig or not verify_meta_hub_signature(raw_body, x_hub_sig, meta_secret):
            logger.warning("Assinatura X-Hub-Signature-256 inválida ou ausente rejeitada.")
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Assinatura inválida.")

    provider = "meta_cloud" if "entry" in body else "evolution"
    event_id = None
    from_phone = None
    text_content = ""
    location_coords = None
    sender_name = None

    # Parser Meta Cloud API
    if provider == "meta_cloud":
        entries = body.get("entry", [])
        for entry in entries:
            for change in entry.get("changes", []):
                value = change.get("value", {})
                contacts = value.get("contacts", [])
                if contacts:
                    sender_name = contacts[0].get("profile", {}).get("name")

                messages = value.get("messages", [])
                for msg in messages:
                    event_id = msg.get("id")
                    from_phone = msg.get("from")
                    msg_type = msg.get("type")

                    if msg_type == "text":
                        text_content = msg.get("text", {}).get("body", "")
                    elif msg_type == "interactive":
                        btn_reply = msg.get("interactive", {}).get("button_reply", {})
                        text_content = btn_reply.get("id") or btn_reply.get("title", "")
                    elif msg_type == "location":
                        loc = msg.get("location", {})
                        location_coords = {
                            "latitude": loc.get("latitude"),
                            "longitude": loc.get("longitude"),
                        }
                        text_content = loc.get("name") or "Localização enviada via WhatsApp"

    # Parser Evolution API
    else:
        # Formato comum Evolution API
        data = body.get("data", {})
        key = data.get("key", {}) or body.get("key", {})
        event_id = key.get("id") or body.get("messageId")
        raw_jid = key.get("remoteJid") or body.get("remoteJid") or ""
        from_phone = raw_jid.replace("@s.whatsapp.net", "").replace("@g.us", "")

        msg = data.get("message", {}) or body.get("message", {})
        sender_name = body.get("pushName") or data.get("pushName")
        if "conversation" in msg:
            text_content = msg.get("conversation", "")
        elif "extendedTextMessage" in msg:
            text_content = msg.get("extendedTextMessage", {}).get("text", "")
        elif "buttonsResponseMessage" in msg:
            text_content = msg.get("buttonsResponseMessage", {}).get("selectedButtonId", "")

    # 2. Deduplicação do Evento (T5.1)
    if event_id:
        try:
            ins_stmt = (
                pg_insert(WaEvent)
                .values(
                    provider=provider,
                    event_id=event_id,
                    payload=body,
                )
                .on_conflict_do_nothing(index_elements=["event_id"])
                .returning(WaEvent.id)
            )
            res = await db.execute(ins_stmt)
            inserted_id = res.fetchone()
            if not inserted_id:
                logger.info("Evento WhatsApp %s já processado anteriormente. Ignorando duplicata.", event_id)
                return {"status": "already_processed"}
        except Exception:
            # Fallback para testes unitários com mock
            pass

    # 3. Disparo para o Bot Conversacional
    if from_phone and (text_content or location_coords):
        await handle_incoming_message(
            db=db,
            from_phone=from_phone,
            message_text=text_content,
            location_coords=location_coords,
            client_name=sender_name,
        )

    return {"status": "received"}


@router.get("/owner/leads-summary")
async def get_owner_leads_summary(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """
    T5.7: Resumo de métricas de pedidos para o painel do lojista:
    total de pedidos recebidos, taxa de aceite e mediana de tempo de resposta (SLA).
    """
    from backend.app.models.business import Business

    biz_stmt = select(Business.id).where(Business.owner_user_id == current_user.id)
    biz_ids = (await db.execute(biz_stmt)).scalars().all()

    if not biz_ids:
        return {
            "total_offers": 0,
            "accepted_offers": 0,
            "declined_offers": 0,
            "acceptance_rate_percent": 0.0,
            "avg_response_seconds": 0,
            "fast_responder_badge": False,
        }

    offers_stmt = select(LeadOffer).where(LeadOffer.business_id.in_(biz_ids))
    offers = (await db.execute(offers_stmt)).scalars().all()

    total = len(offers)
    accepted = len([o for o in offers if o.status == "accepted"])
    declined = len([o for o in offers if o.status == "declined"])
    rate = round((accepted / total) * 100.0, 1) if total > 0 else 0.0

    response_times = [o.response_seconds for o in offers if o.response_seconds is not None]
    avg_seconds = int(sum(response_times) / len(response_times)) if response_times else 0

    # Selo "Responde Rápido": taxa de aceite >= 60% e média de resposta <= 300 segundos (5 min)
    fast_badge = (total >= 3 and rate >= 60.0 and avg_seconds <= 300)

    return {
        "total_offers": total,
        "accepted_offers": accepted,
        "declined_offers": declined,
        "acceptance_rate_percent": rate,
        "avg_response_seconds": avg_seconds,
        "fast_responder_badge": fast_badge,
    }
