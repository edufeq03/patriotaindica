import json
import logging
import re
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional
from uuid import UUID

from sqlalchemy import func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from geoalchemy2 import Geography

from backend.app.core.redis_client import get_redis_client
from backend.app.models.business import Business, BusinessCategory
from backend.app.models.category import Category
from backend.app.models.lead import Lead, LeadOffer
from backend.app.models.subscription import Plan, Subscription
from backend.app.models.whatsapp import WaOptin
from backend.app.services.whatsapp.base import WhatsAppButton, clean_phone_number
from backend.app.services.whatsapp.factory import get_whatsapp_service

logger = logging.getLogger("patriotaindica.whatsapp.bot")

# Fallback em memória caso o Redis não esteja disponível
_MEMORY_STATE: Dict[str, Dict[str, Any]] = {}


async def get_conversation_state(phone_e164: str) -> Dict[str, Any]:
    redis = get_redis_client()
    key = f"wa_state:{phone_e164}"
    if redis:
        try:
            val = await redis.get(key)
            if val:
                return json.loads(val)
        except Exception as e:
            logger.warning("Falha ao ler estado do Redis (%s), usando fallback em memória: %s", key, e)

    return _MEMORY_STATE.get(phone_e164, {"step": "IDLE"})


async def set_conversation_state(phone_e164: str, state_data: Dict[str, Any], ttl_seconds: int = 1800) -> None:
    redis = get_redis_client()
    key = f"wa_state:{phone_e164}"
    if redis:
        try:
            await redis.set(key, json.dumps(state_data), ex=ttl_seconds)
            return
        except Exception as e:
            logger.warning("Falha ao salvar estado no Redis (%s): %s", key, e)

    _MEMORY_STATE[phone_e164] = state_data


async def clear_conversation_state(phone_e164: str) -> None:
    redis = get_redis_client()
    key = f"wa_state:{phone_e164}"
    if redis:
        try:
            await redis.delete(key)
        except Exception:
            pass
    _MEMORY_STATE.pop(phone_e164, None)


async def check_opt_out(db: AsyncSession, phone_e164: str) -> bool:
    """Verifica se o número solicitou opt-out ('PARAR' / 'SAIR')."""
    stmt = select(WaOptin).where(
        WaOptin.phone_e164 == phone_e164,
        WaOptin.status == "revoked",
    )
    revoked = (await db.execute(stmt)).scalars().first()
    return revoked is not None


async def handle_incoming_message(
    db: AsyncSession,
    from_phone: str,
    message_text: str,
    location_coords: Optional[Dict[str, float]] = None,
    client_name: Optional[str] = None,
) -> bool:
    """
    Motor central da máquina de estados conversacional do WhatsApp.
    Processa mensagens de texto e pin de localização geográfica.
    """
    phone_e164 = f"+{clean_phone_number(from_phone)}"
    clean_text = message_text.strip()
    upper_text = clean_text.upper()
    whatsapp_svc = get_whatsapp_service()

    # 1. Tratamento de Opt-Out e Opt-In (LGPD e Regras Meta)
    if upper_text in ("PARAR", "SAIR", "STOP", "CANCELAR"):
        optin_stmt = select(WaOptin).where(WaOptin.phone_e164 == phone_e164)
        optin = (await db.execute(optin_stmt)).scalars().first()
        now = datetime.now(timezone.utc)
        if optin:
            optin.status = "revoked"
            optin.revoked_at = now
        else:
            db.add(WaOptin(phone_e164=phone_e164, status="revoked", revoked_at=now))
        await db.commit()
        await clear_conversation_state(phone_e164)
        await whatsapp_svc.send_text(
            to_phone=phone_e164,
            text="🛑 *Atendimento cancelado.*\n\nVocê não receberá mais mensagens automáticas do Patriota Indica. Para reativar quando precisar, responda com *VOLTAR*.",
        )
        return True

    if upper_text in ("VOLTAR", "START", "REATIVAR"):
        optin_stmt = select(WaOptin).where(WaOptin.phone_e164 == phone_e164)
        optin = (await db.execute(optin_stmt)).scalars().first()
        if optin:
            optin.status = "active"
            optin.revoked_at = None
        else:
            db.add(WaOptin(phone_e164=phone_e164, status="active"))
        await db.commit()
        await clear_conversation_state(phone_e164)
        await whatsapp_svc.send_text(
            to_phone=phone_e164,
            text="✅ *Notificações reativadas com sucesso!*\n\nComo o Patriota Indica pode ajudar você hoje?",
        )
        return True

    # 2. Tratamento de Resposta do Lojista a Oferta de Lead (ACEITAR / RECUSAR)
    match_accept = re.search(r"(?:ACEITAR|ACEITO|SIM|ACCEPT)\s*[:_-]?\s*([A-Za-z0-9]{4,10})", upper_text)
    match_decline = re.search(r"(?:RECUSAR|RECUSO|NAO|NÃO|DECLINE)\s*[:_-]?\s*([A-Za-z0-9]{4,10})", upper_text)

    if match_accept or match_decline:
        offer_code = (match_accept.group(1) if match_accept else match_decline.group(1)).upper()
        is_accept = match_accept is not None

        offer_stmt = (
            select(LeadOffer)
            .where(func.upper(LeadOffer.offer_code) == offer_code)
        )
        offer = (await db.execute(offer_stmt)).scalars().first()

        if not offer:
            await whatsapp_svc.send_text(
                to_phone=phone_e164,
                text="⚠️ Código de pedido não encontrado ou expirado. Verifique o código e tente novamente.",
            )
            return True

        lead = (await db.execute(select(Lead).where(Lead.id == offer.lead_id))).scalars().first()
        business = (await db.execute(select(Business).where(Business.id == offer.business_id))).scalars().first()
        now = datetime.now(timezone.utc)

        if not is_accept:
            offer.status = "declined"
            offer.responded_at = now
            await db.commit()
            await whatsapp_svc.send_text(to_phone=phone_e164, text="👍 Oferta recusada. Novas oportunidades serão enviadas assim que surgirem.")
            return True

        # Caso de Aceite
        if lead.status == "matched":
            await whatsapp_svc.send_text(
                to_phone=phone_e164,
                text="⏳ *Pedido já atendido!*\n\nOutro profissional parceiro aceitou este pedido alguns instantes antes. Fique atento às próximas notificações para ser o primeiro!",
            )
            return True

        # Primeiro aceite fecha o pedido com exclusividade
        lead.status = "matched"
        lead.matched_business_id = business.id
        offer.status = "accepted"
        offer.responded_at = now
        if offer.sent_at:
            offer.response_seconds = int((now - offer.sent_at).total_seconds())

        await db.commit()

        # Notificar o lojista com o contato do cliente com espírito de rede
        client_digits = clean_phone_number(lead.client_phone_e164)
        await whatsapp_svc.send_text(
            to_phone=phone_e164,
            text=(
                f"🤝 *Conexão Realizada com Sucesso!*\n\n"
                f"O Patriota Indica conectou você a um cliente da nossa rede:\n\n"
                f"👤 *Cliente:* {lead.client_name or 'Cliente da Rede'}\n"
                f"📱 *WhatsApp do Cliente:* https://wa.me/{client_digits}\n"
                f"📝 *Necessidade informada:* {lead.description}\n\n"
                f"O cliente já recebeu a sua indicação, mas você já pode chamá-lo diretamente pelo link acima para apresentar seus serviços com a credibilidade de um negócio verificado!"
            ),
        )

        # Notificar o cliente conectando com a empresa recomendada
        await whatsapp_svc.send_text(
            to_phone=lead.client_phone_e164,
            text=(
                f"🇧🇷 *Indicação Confiável da Rede Patriota Indica!*\n\n"
                f"Temos o prazer de indicar um parceiro verificado e recomendado da nossa rede:\n\n"
                f"🏢 *{business.name}*\n"
                f"📍 *Localização:* {business.neighborhood}, {business.city} - {business.state}\n"
                f"📱 *Conversar no WhatsApp:* https://wa.me/{clean_phone_number(business.whatsapp)}\n\n"
                f"O empresário já foi notificado da sua busca. Você já pode chamá-lo diretamente pelo link acima com a tranquilidade de negociar com quem tem valores alinhados e curadoria aprovada!"
            ),
        )
        return True


    # 3. Fluxo de Captação de Orçamento (Cliente Iniciando Conversa)
    state = await get_conversation_state(phone_e164)
    step = state.get("step", "IDLE")

    if step == "IDLE":
        # Iniciar novo pedido de orçamento
        new_state = {
            "step": "AWAITING_NEED",
            "client_name": client_name or "Cliente",
            "started_at": datetime.now(timezone.utc).isoformat(),
        }
        await set_conversation_state(phone_e164, new_state)
        await whatsapp_svc.send_text(
            to_phone=phone_e164,
            text=(
                "👋 Olá! Bem-vindo ao *Patriota Indica*, a rede que conecta você aos melhores profissionais e comércios da sua região!\n\n"
                "🛠️ *O que você está precisando hoje?*\n"
                "_Exemplo: Eletricista para troca de fiação, Pintor de paredes, Mecânico para revisão, Bolos para festa, etc._"
            ),
        )
        return True

    if step == "AWAITING_NEED":
        description = clean_text
        # Tentar identificar categoria
        cat_stmt = select(Category).order_by(Category.name.asc())
        categories = (await db.execute(cat_stmt)).scalars().all()
        matched_cat = None
        for cat in categories:
            if cat.name.lower() in description.lower():
                matched_cat = cat
                break

        state["step"] = "AWAITING_LOCATION"
        state["description"] = description
        state["category_id"] = str(matched_cat.id) if matched_cat else None
        await set_conversation_state(phone_e164, state)

        await whatsapp_svc.send_text(
            to_phone=phone_e164,
            text=(
                "Perfeito! 📍 *Onde o serviço deve ser realizado?*\n\n"
                "Você pode:\n"
                "1. Enviar sua localização atual usando o botão de *Anexo 📎 -> Localização* do WhatsApp\n"
                "2. Ou digitar seu *Bairro e Cidade* (ex: Centro, Campinas - SP)"
            ),
        )
        return True

    if step == "AWAITING_LOCATION":
        description = state.get("description", "Serviço solicitado via WhatsApp")
        cat_id_str = state.get("category_id")
        category_uuid = UUID(cat_id_str) if cat_id_str else None

        lat = location_coords.get("latitude") if location_coords else None
        lng = location_coords.get("longitude") if location_coords else None
        loc_geog = f"SRID=4326;POINT({lng} {lat})" if (lat and lng) else None

        city = None
        state_uf = None
        if not loc_geog and clean_text:
            parts = clean_text.split(",")
            city = parts[0].strip()
            if len(parts) > 1:
                state_uf = parts[1].strip().upper()[:2]

        # Criar Lead
        new_lead = Lead(
            client_phone_e164=phone_e164,
            client_name=state.get("client_name"),
            category_id=category_uuid,
            description=description,
            urgency="normal",
            location=loc_geog,
            city=city,
            state=state_uf,
            status="pending_offers",
        )
        db.add(new_lead)
        await db.flush()

        # Buscar até 3 empresas aprovadas para enviar o pedido
        biz_query = (
            select(Business)
            .outerjoin(
                Subscription,
                (Subscription.owner_user_id == Business.owner_user_id)
                & (Subscription.status.in_(["active", "grace_period"])),
            )
            .outerjoin(Plan, Plan.id == Subscription.plan_id)
            .where(
                Business.status == "approved",
                Business.owner_paused.is_(False),
            )
        )
        if category_uuid:
            biz_query = biz_query.join(
                BusinessCategory,
                (BusinessCategory.business_id == Business.id) & (BusinessCategory.category_id == category_uuid),
            )
        if city:
            biz_query = biz_query.where(Business.city.ilike(f"%{city}%"))

        # Priorizar empresas com plano ativo e busca prioritária
        biz_query = biz_query.order_by(
            func.coalesce(Plan.search_priority, 1).desc(),
            Business.is_verified.desc(),
            Business.created_at.desc(),
        ).limit(3)

        matched_businesses = (await db.execute(biz_query)).scalars().all()

        offers_sent = 0
        now = datetime.now(timezone.utc)
        for b in matched_businesses:
            offer_code = secrets.token_hex(2).upper()  # Ex: 'A8B2'
            offer = LeadOffer(
                lead_id=new_lead.id,
                business_id=b.id,
                offer_code=offer_code,
                status="sent",
                sent_at=now,
            )
            db.add(offer)

            # Notificar empresa parceira com foco em rede de negócios
            target_phone = b.whatsapp_e164 or b.whatsapp
            msg_offer = (
                f"🤝 *Nova Oportunidade de Indicação na Rede Patriota Indica!*\n\n"
                f"📍 *Região do Cliente:* {city or b.city or 'Sua região'}\n"
                f"📝 *Necessidade:* \"{description}\"\n\n"
                f"Você tem disponibilidade para atender este cliente indicado pela nossa rede?\n\n"
                f"👉 Para confirmar atendimento: *ACEITAR {offer_code}*\n"
                f"👉 Para dispensar no momento: *RECUSAR {offer_code}*"
            )
            buttons = [
                WhatsAppButton(id=f"ACEITAR {offer_code}", title="Atender Indicação"),
                WhatsAppButton(id=f"RECUSAR {offer_code}", title="Dispensar"),
            ]
            await whatsapp_svc.send_buttons(to_phone=target_phone, text=msg_offer, buttons=buttons)
            offers_sent += 1

        await db.commit()
        await clear_conversation_state(phone_e164)

        if offers_sent > 0:
            await whatsapp_svc.send_text(
                to_phone=phone_e164,
                text=(
                    "🇧🇷 *Indicação em andamento!*\n\n"
                    f"Já direcionamos sua solicitação aos parceiros verificados e recomendados da nossa rede na sua região. "
                    "Assim que confirmarem a disponibilidade, você receberá a indicação completa diretamente aqui no WhatsApp!"
                ),
            )
        else:
            await whatsapp_svc.send_text(
                to_phone=phone_e164,
                text=(
                    "🇧🇷 *Solicitação registrada!*\n\n"
                    "Nossa equipe de curadoria está selecionando os melhores parceiros confiáveis da sua localidade para conectar com você em breve."
                ),
            )
        return True


    return True
