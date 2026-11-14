import hashlib
import hmac
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from backend.app.core.config import settings
from backend.app.core.database import get_db
from backend.app.core.security import get_current_user
from backend.app.main import app
from backend.app.models.business import Business
from backend.app.models.category import Category
from backend.app.models.lead import Lead, LeadOffer
from backend.app.models.user import User
from backend.app.models.whatsapp import WaEvent, WaOptin
from backend.app.services.whatsapp.bot import (
    clear_conversation_state,
    get_conversation_state,
    handle_incoming_message,
    set_conversation_state,
)
from backend.app.services.whatsapp.evolution import EvolutionWhatsAppProvider
from backend.app.services.whatsapp.factory import (
    ConsoleWhatsAppProvider,
    get_whatsapp_service,
)
from backend.app.services.whatsapp.meta_cloud import MetaCloudWhatsAppProvider

client = TestClient(app)


@pytest.mark.skipif(not settings.FEATURE_WHATSAPP_BOT, reason="Bot de WhatsApp congelado no MVP por FEATURE_WHATSAPP_BOT")
def test_t5_1_meta_webhook_verification_get():
    """T5.1: Verificação oficial do Webhook da Meta Cloud API com hub.challenge e hub.verify_token."""
    verify_token = settings.META_WHATSAPP_VERIFY_TOKEN
    challenge = "1155998822"

    # 1. Token correto -> Retorna challenge (200)
    res_ok = client.get(
        f"/api/v1/webhooks/whatsapp?hub.mode=subscribe&hub.verify_token={verify_token}&hub.challenge={challenge}"
    )
    assert res_ok.status_code == 200
    assert res_ok.text == challenge

    # 2. Token incorreto -> Retorna 403 Forbidden
    res_fail = client.get(
        f"/api/v1/webhooks/whatsapp?hub.mode=subscribe&hub.verify_token=token_invalido&hub.challenge={challenge}"
    )
    assert res_fail.status_code == 403


@pytest.mark.skipif(not settings.FEATURE_WHATSAPP_BOT, reason="Bot de WhatsApp congelado no MVP por FEATURE_WHATSAPP_BOT")
def test_t5_1_meta_webhook_signature_validation():
    """T5.1: Validação de assinatura criptográfica X-Hub-Signature-256 no POST de eventos da Meta."""
    app_secret = "meta_test_secret_key_123"
    raw_payload = b'{"entry": [{"changes": [{"value": {"messages": [{"id": "wamid.123", "from": "5511999990001", "type": "text", "text": {"body": "Ola"}}]}}]}]}'

    calc_sig = hmac.new(app_secret.encode("utf-8"), raw_payload, hashlib.sha256).hexdigest()
    valid_header = f"sha256={calc_sig}"

    with patch.object(settings, "META_APP_SECRET", app_secret):
        # 1. Assinatura válida -> 200
        res_ok = client.post(
            "/api/v1/webhooks/whatsapp",
            headers={"X-Hub-Signature-256": valid_header, "Content-Type": "application/json"},
            content=raw_payload,
        )
        assert res_ok.status_code == 200

        # 2. Assinatura inválida -> 401
        res_fail = client.post(
            "/api/v1/webhooks/whatsapp",
            headers={"X-Hub-Signature-256": "sha256=invalid_hash", "Content-Type": "application/json"},
            content=raw_payload,
        )
        assert res_fail.status_code == 401


def test_t5_2_hybrid_provider_selection():
    """T5.2: Factory seleciona dinamicamente Evolution API ou Meta Cloud API de forma desacoplada."""
    # 1. Configurado como Evolution
    with patch.object(settings, "WHATSAPP_PROVIDER", "evolution"):
        with patch.object(settings, "EVOLUTION_API_URL", "https://evolution.teste.com"):
            with patch.object(settings, "EVOLUTION_API_KEY", "key123"):
                with patch.object(settings, "EVOLUTION_INSTANCE_NAME", "inst_teste"):
                    provider = get_whatsapp_service()
                    assert isinstance(provider, EvolutionWhatsAppProvider)
                    assert provider.provider_name == "evolution"

    # 2. Configurado como Meta Cloud API Oficial
    with patch.object(settings, "WHATSAPP_PROVIDER", "meta_cloud"):
        with patch.object(settings, "META_WHATSAPP_ACCESS_TOKEN", "token_meta_123"):
            with patch.object(settings, "META_WHATSAPP_PHONE_NUMBER_ID", "phone_id_456"):
                provider = get_whatsapp_service()
                assert isinstance(provider, MetaCloudWhatsAppProvider)
                assert provider.provider_name == "meta_cloud"

    # 3. Sem credenciais -> Fallback seguro Console
    with patch.object(settings, "WHATSAPP_PROVIDER", "console"):
        provider = get_whatsapp_service()
        assert isinstance(provider, ConsoleWhatsAppProvider)
        assert provider.provider_name == "console"


@pytest.mark.anyio
async def test_t5_3_bot_quote_request_flow_and_lead_matching():
    """T5.3: Fluxo conversacional do bot captando necessidade e localização do cliente."""
    client_phone = "+5519988776655"
    await clear_conversation_state(client_phone)

    mock_db = AsyncMock()

    # 1. Cliente manda mensagem inicial -> Bot pergunta o que precisa
    res = await handle_incoming_message(
        db=mock_db,
        from_phone=client_phone,
        message_text="Olá, preciso de um orçamento",
    )
    assert res is True
    st1 = await get_conversation_state(client_phone)
    assert st1.get("step") == "AWAITING_NEED"

    # 2. Cliente informa o que precisa -> Bot pergunta localização
    mock_res_cats = MagicMock()
    mock_res_cats.scalars.return_value.all.return_value = []
    mock_db.execute.return_value = mock_res_cats

    res2 = await handle_incoming_message(
        db=mock_db,
        from_phone=client_phone,
        message_text="Preciso de um encanador para consertar vazamento",
    )
    assert res2 is True
    st2 = await get_conversation_state(client_phone)
    assert st2.get("step") == "AWAITING_LOCATION"
    assert "encanador" in st2.get("description", "").lower()

    await clear_conversation_state(client_phone)


@pytest.mark.anyio
async def test_t5_3_lead_offer_first_to_accept_wins():
    """T5.3: Primeiro lojista a responder ACEITAR fecha o pedido e os seguintes são avisados."""
    lead_id = uuid4()
    biz_id_1 = uuid4()
    biz_id_2 = uuid4()

    mock_lead = Lead(
        id=lead_id,
        client_phone_e164="+5519988881111",
        client_name="Maria Silva",
        description="Pintura de sala",
        status="pending_offers",
    )

    mock_biz_1 = Business(
        id=biz_id_1,
        name="Pinturas Silva",
        whatsapp="19999991111",
        neighborhood="Centro",
        city="Campinas",
        state="SP",
    )

    mock_offer_1 = LeadOffer(
        id=uuid4(),
        lead_id=lead_id,
        business_id=biz_id_1,
        offer_code="A1B2",
        status="sent",
        sent_at=datetime.now(timezone.utc),
    )

    mock_db = AsyncMock()

    # Cenário 1: Primeiro lojista aceita
    mock_res_offer = MagicMock()
    mock_res_offer.scalars.return_value.first.return_value = mock_offer_1

    mock_res_lead = MagicMock()
    mock_res_lead.scalars.return_value.first.return_value = mock_lead

    mock_res_biz = MagicMock()
    mock_res_biz.scalars.return_value.first.return_value = mock_biz_1

    mock_db.execute.side_effect = [mock_res_offer, mock_res_lead, mock_res_biz]

    res = await handle_incoming_message(
        db=mock_db,
        from_phone="+5519999991111",
        message_text="ACEITAR A1B2",
    )
    assert res is True
    assert mock_lead.status == "matched"
    assert mock_lead.matched_business_id == biz_id_1
    assert mock_offer_1.status == "accepted"
    assert mock_offer_1.response_seconds is not None

    # Cenário 2: Segundo lojista tenta aceitar depois -> Pedido já atendido
    mock_offer_2 = LeadOffer(
        id=uuid4(),
        lead_id=lead_id,
        business_id=biz_id_2,
        offer_code="C3D4",
        status="sent",
        sent_at=datetime.now(timezone.utc),
    )
    mock_res_offer2 = MagicMock()
    mock_res_offer2.scalars.return_value.first.return_value = mock_offer_2

    # Lead agora já está com status 'matched'
    mock_db.execute.side_effect = [mock_res_offer2, mock_res_lead, mock_res_biz]

    res2 = await handle_incoming_message(
        db=mock_db,
        from_phone="+5519999992222",
        message_text="ACEITAR C3D4",
    )
    assert res2 is True
    # Lead permanece com a primeira empresa e a oferta 2 não é aceita
    assert mock_lead.matched_business_id == biz_id_1
    assert mock_offer_2.status != "accepted"


@pytest.mark.anyio
async def test_t5_1_opt_out_lgpd_parar_keyword():
    """T5.1 & LGPD: Palavra-chave PARAR silencia mensagens e marca opt-out revogado."""
    user_phone = "+5511977778888"
    mock_db = AsyncMock()

    mock_res_optin = MagicMock()
    mock_res_optin.scalars.return_value.first.return_value = None
    mock_db.execute.return_value = mock_res_optin

    res = await handle_incoming_message(
        db=mock_db,
        from_phone=user_phone,
        message_text="PARAR",
    )
    assert res is True
    # db.add deve ter sido chamado para gravar o WaOptin com status revoked
    assert mock_db.add.called
    added_obj = mock_db.add.call_args[0][0]
    assert isinstance(added_obj, WaOptin)
    assert added_obj.status == "revoked"


@pytest.mark.skipif(not settings.FEATURE_WHATSAPP_BOT, reason="Bot de WhatsApp congelado no MVP por FEATURE_WHATSAPP_BOT")
def test_t5_7_owner_leads_summary_and_fast_responder_badge():
    """T5.7: Endpoint /owner/leads-summary calcula taxa de aceite, média de SLA e selo Responde Rápido."""
    owner_id = uuid4()
    mock_owner = User(
        id=owner_id,
        name="Lojista Agil",
        email="agil@lojista.com",
        phone="+5519999990000",
        role="owner",
        is_active=True,
    )

    async def override_user():
        return mock_owner

    biz_id = uuid4()

    # 4 ofertas: 3 aceitas com média de 120s (2 min) -> Ativa o selo Responde Rápido
    o1 = LeadOffer(id=uuid4(), business_id=biz_id, status="accepted", response_seconds=100)
    o2 = LeadOffer(id=uuid4(), business_id=biz_id, status="accepted", response_seconds=140)
    o3 = LeadOffer(id=uuid4(), business_id=biz_id, status="accepted", response_seconds=120)
    o4 = LeadOffer(id=uuid4(), business_id=biz_id, status="declined", response_seconds=None)

    async def override_db():
        mock_db = AsyncMock()
        mock_res_biz = MagicMock()
        mock_res_biz.scalars.return_value.all.return_value = [biz_id]

        mock_res_offers = MagicMock()
        mock_res_offers.scalars.return_value.all.return_value = [o1, o2, o3, o4]

        mock_db.execute.side_effect = [mock_res_biz, mock_res_offers]
        yield mock_db

    app.dependency_overrides[get_current_user] = override_user
    app.dependency_overrides[get_db] = override_db
    try:
        res = client.get("/api/v1/webhooks/whatsapp/owner/leads-summary")
        assert res.status_code == 200
        data = res.json()
        assert data["total_offers"] == 4
        assert data["accepted_offers"] == 3
        assert data["acceptance_rate_percent"] == 75.0
        assert data["avg_response_seconds"] == 120
        assert data["fast_responder_badge"] is True
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(get_db, None)

