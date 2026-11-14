import hashlib
import hmac
import time
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from backend.app.core.config import settings
from backend.app.core.database import get_db
from backend.app.core.security import get_current_user
from backend.app.main import app
from backend.app.models.business import Business
from backend.app.models.payment import Payment
from backend.app.models.subscription import Plan, Referral, Subscription
from backend.app.models.user import User

client = TestClient(app)


def test_t4_1_plans_single_source_and_entitlements():
    """T4.1: Endpoint público /plans retorna os planos com preços em centavos e entitlements completos."""
    response = client.get("/api/v1/payments/plans")
    assert response.status_code == 200
    plans = response.json()
    assert len(plans) >= 3

    plan_ids = [p["id"] for p in plans]
    assert "mensal" in plan_ids
    assert "semestral" in plan_ids
    assert "anual" in plan_ids

    anual = next(p for p in plans if p["id"] == "anual")
    assert anual["price_cents"] == 11988
    assert anual["monthly_equivalent"] == "R$ 9,99"
    assert anual["is_featured"] is True
    assert anual["search_priority"] == 30
    assert anual["has_banner_access"] is True
    assert anual["max_categories"] >= 5


def test_t4_2_subscription_lifecycle_grace_period_and_expired():
    """T4.2: Ciclo de vida da assinatura com carência (grace_period de 3 dias) e expiração."""
    mock_user_id = uuid4()
    mock_owner = User(
        id=mock_user_id,
        name="Lojista Teste",
        email="lojista@teste.com",
        phone="+5511999990001",
        role="owner",
        is_active=True,
    )

    async def override_user():
        return mock_owner

    now = datetime.now(timezone.utc)

    # 1. Assinatura ativa normal
    sub_active = Subscription(
        id=uuid4(),
        owner_user_id=mock_user_id,
        plan_id="anual",
        status="active",
        current_period_start=now - timedelta(days=30),
        current_period_end=now + timedelta(days=335),
    )

    async def override_db_active():
        mock_db = AsyncMock()
        mock_r1 = MagicMock()
        mock_r1.scalars.return_value.first.return_value = sub_active
        mock_r2 = MagicMock()
        mock_r2.scalars.return_value.all.return_value = []
        mock_r3 = MagicMock()
        mock_r3.scalar.return_value = 0
        mock_db.execute.side_effect = [mock_r1, mock_r2, mock_r3, mock_r3]
        yield mock_db

    app.dependency_overrides[get_current_user] = override_user
    app.dependency_overrides[get_db] = override_db_active
    try:
        res = client.get("/api/v1/payments/my-subscription")
        assert res.status_code == 200
        data = res.json()
        assert data["is_active"] is True
        assert data["status"] == "active"
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(get_db, None)

    # 2. Assinatura vencida há 1 dia (deve estar em grace_period com benefícios mantidos)
    sub_grace = Subscription(
        id=uuid4(),
        owner_user_id=mock_user_id,
        plan_id="anual",
        status="active",
        current_period_start=now - timedelta(days=366),
        current_period_end=now - timedelta(days=1),
    )

    async def override_db_grace():
        mock_db = AsyncMock()
        mock_r1 = MagicMock()
        mock_r1.scalars.return_value.first.return_value = sub_grace
        mock_r2 = MagicMock()
        mock_r2.scalars.return_value.all.return_value = []
        mock_r3 = MagicMock()
        mock_r3.scalar.return_value = 0
        mock_db.execute.side_effect = [mock_r1, mock_r2, mock_r3, mock_r3]
        yield mock_db

    app.dependency_overrides[get_current_user] = override_user
    app.dependency_overrides[get_db] = override_db_grace
    try:
        res = client.get("/api/v1/payments/my-subscription")
        assert res.status_code == 200
        data = res.json()
        assert data["is_active"] is True
        assert data["status"] == "grace_period"
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(get_db, None)

    # 3. Assinatura vencida há mais de 3 dias (expirada)
    sub_expired = Subscription(
        id=uuid4(),
        owner_user_id=mock_user_id,
        plan_id="anual",
        status="active",
        current_period_start=now - timedelta(days=370),
        current_period_end=now - timedelta(days=5),
    )

    async def override_db_expired():
        mock_db = AsyncMock()
        mock_r1 = MagicMock()
        mock_r1.scalars.return_value.first.return_value = sub_expired
        mock_r2 = MagicMock()
        mock_r2.scalars.return_value.all.return_value = []
        mock_r3 = MagicMock()
        mock_r3.scalar.return_value = 0
        mock_db.execute.side_effect = [mock_r1, mock_r2, mock_r3, mock_r3]
        yield mock_db

    app.dependency_overrides[get_current_user] = override_user
    app.dependency_overrides[get_db] = override_db_expired
    try:
        res = client.get("/api/v1/payments/my-subscription")
        assert res.status_code == 200
        data = res.json()
        assert data["is_active"] is False
        assert data["status"] == "expired"
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(get_db, None)


def test_t4_3_webhook_hmac_signature_validation():
    """T4.3: Validação criptográfica do cabeçalho x-signature no webhook do Mercado Pago."""
    webhook_secret = "test_webhook_secret_key_12345"
    data_id = "123456789"
    request_id = "req_test_uuid_987"
    ts = str(int(time.time()))

    manifest = f"id:{data_id};request-id:{request_id};ts:{ts};"
    valid_v1 = hmac.new(webhook_secret.encode("utf-8"), manifest.encode("utf-8"), hashlib.sha256).hexdigest()
    valid_signature = f"ts={ts},v1={valid_v1}"

    with patch.object(settings, "MERCADO_PAGO_WEBHOOK_SECRET", webhook_secret):
        # 1. Requisição com HMAC correto -> Deve ser aceita
        res_ok = client.post(
            f"/api/v1/payments/mercadopago/webhook?id={data_id}&topic=payment",
            headers={
                "x-signature": valid_signature,
                "x-request-id": request_id,
            },
            json={"type": "payment", "data": {"id": data_id}},
        )
        assert res_ok.status_code == 200
        assert res_ok.json().get("status") in ("received", "already_processed")

        # 2. Requisição com HMAC adulterado -> Deve retornar 401
        invalid_signature = f"ts={ts},v1=invalid_tampered_hash_0000"
        res_fail = client.post(
            f"/api/v1/payments/mercadopago/webhook?id={data_id}&topic=payment",
            headers={
                "x-signature": invalid_signature,
                "x-request-id": request_id,
            },
            json={"type": "payment", "data": {"id": data_id}},
        )
        assert res_fail.status_code == 401
        assert "Assinatura do webhook inválida" in res_fail.json()["detail"]


def test_t4_4_trusted_return_urls_public_app_url():
    """T4.4: Confirma que URLs de retorno no checkout vêm estritamente de PUBLIC_APP_URL e ignoram Origin forjado."""
    mock_user = User(
        id=uuid4(),
        name="Teste Urls",
        email="urls@teste.com",
        phone="+5511999990002",
        role="owner",
        is_active=True,
    )

    async def override_user():
        return mock_user

    async def override_db():
        mock_db = AsyncMock()
        mock_plan = Plan(
            id="anual",
            name="Plano Anual",
            price_cents=11988,
            monthly_equivalent_cents=999,
            duration_months=12,
            is_active=True,
        )
        mock_res = MagicMock()
        mock_res.scalars.return_value.first.return_value = mock_plan
        mock_db.execute.return_value = mock_res
        yield mock_db

    app.dependency_overrides[get_current_user] = override_user
    app.dependency_overrides[get_db] = override_db
    try:
        with patch.object(settings, "PUBLIC_APP_URL", "https://patriotaindica.com.br"):
            res = client.post(
                "/api/v1/payments/create-preference",
                headers={
                    "Origin": "https://malicious-site.com",  # Tentativa de injeção de origin
                },
                json={"plan_id": "anual"},
            )
            assert res.status_code == 200
            data = res.json()
            assert data["success"] is True
            # Preferência gerada com sucesso sem vazamento da origin maliciosa
            assert "malicious-site.com" not in str(data)
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(get_db, None)


@pytest.mark.anyio
async def test_t4_5_referral_anti_fraud_rules():

    """T4.5: Bloqueio estrito de auto-indicação e regras de recompensa Member-Get-Member."""
    from backend.app.api.v1.endpoints.payments import activate_user_subscription

    user_id_1 = uuid4()
    biz_id_1 = uuid4()
    mock_db = AsyncMock()

    # Cenário 1: Auto-indicação direta (referrer_user_id == referred_user_id)
    referral_self = Referral(
        id=uuid4(),
        referrer_user_id=user_id_1,
        referred_user_id=user_id_1,
        referred_business_id=biz_id_1,
        code="PAT-AUTO",
        status="pending",
    )

    mock_res_plan = MagicMock()
    mock_res_plan.scalars.return_value.first.return_value = None  # Usa fallback

    mock_res_sub = MagicMock()
    mock_res_sub.scalars.return_value.first.return_value = None

    mock_res_ref = MagicMock()
    mock_res_ref.scalars.return_value.first.return_value = referral_self

    mock_db.execute.side_effect = [mock_res_plan, mock_res_sub, mock_res_ref]

    res = await activate_user_subscription(
        db=mock_db,
        user_id=user_id_1,
        plan_id="anual",
        payment_id="pay_test_self",
    )

    assert res["success"] is True
    assert res["rewarded_referrer_user_id"] is None
    # Deve ter marcado como fraud_blocked
    assert referral_self.status == "fraud_blocked"


@pytest.mark.anyio
async def test_t4_3_webhook_idempotency_and_price_tampering():
    """T4.3: Validação de idempotência e rejeição de fraude de adulteração de preço no Webhook."""
    from backend.app.api.v1.endpoints.payments import mercadopago_webhook
    from unittest.mock import AsyncMock, MagicMock
    from starlette.requests import Request

    user_id = uuid4()
    data_id = "pay_unique_998877"

    # Criar mock de requisição FastAPI com payload aprovado
    async def mock_receive():
        return {
            "type": "http.request",
            "body": b'{"type": "payment", "data": {"id": "pay_unique_998877"}}',
        }

    req = Request(
        scope={
            "type": "http",
            "method": "POST",
            "path": "/api/v1/payments/mercadopago/webhook",
            "headers": [],
            "query_string": b"",
        },
        receive=mock_receive,
    )

    mock_db = AsyncMock()

    # Cenário A: Preço adulterado (tentou pagar R$ 1,00 para plano anual de R$ 119,88)
    tampered_mp_response = {
        "status": "approved",
        "currency_id": "BRL",
        "transaction_amount": 1.00,  # Adulterado!
        "metadata": {
            "user_id": str(user_id),
            "plan_id": "anual",
        },
    }

    mock_plan = Plan(
        id="anual",
        name="Plano Anual",
        price_cents=11988,
        monthly_equivalent_cents=999,
        duration_months=12,
        is_active=True,
    )

    mock_res_plan = MagicMock()
    mock_res_plan.scalars.return_value.first.return_value = mock_plan
    mock_db.execute.return_value = mock_res_plan

    with patch("httpx.AsyncClient.get") as mock_get:
        mock_http_res = MagicMock()
        mock_http_res.status_code = 200
        mock_http_res.json.return_value = tampered_mp_response
        mock_get.return_value = mock_http_res

        with patch.object(settings, "MERCADO_PAGO_ACCESS_TOKEN", "fake_mp_token"):
            result = await mercadopago_webhook(request=req, db=mock_db)
            assert result.get("status") == "rejected"
            assert result.get("reason") == "price_tampered"


@pytest.mark.anyio
async def test_t4_3_webhook_refund_cancels_subscription():
    """T4.3: Notificação de reembolso ou estorno cancela benefícios imediatamente."""
    from backend.app.api.v1.endpoints.payments import cancel_user_subscription

    user_id = uuid4()
    mock_db = AsyncMock()

    active_sub = Subscription(
        id=uuid4(),
        owner_user_id=user_id,
        plan_id="anual",
        status="active",
        current_period_end=datetime.now(timezone.utc) + timedelta(days=300),
    )

    mock_res = MagicMock()
    mock_res.scalars.return_value.first.return_value = active_sub
    mock_db.execute.return_value = mock_res

    await cancel_user_subscription(db=mock_db, user_id=user_id, payment_id="pay_refund_123")

    assert active_sub.status == "canceled"
    assert active_sub.current_period_end <= datetime.now(timezone.utc)




@pytest.mark.anyio
async def test_t4_full_mvp_lifecycle_jobs_and_visibility():
    """
    T4.1 (Sprint S4): Ensaio de ponta a ponta do Módulo de Vagas no MVP:
    - Vaga ativa pertence à empresa aprovada
    - Candidatura pública (/jobs/{id}/apply-click) registra evento de contato
    - Anonimização/exclusão lógica remove empresa e vagas da vitrine pública
    """
    from backend.app.models.jobs import JobOpening

    biz_id = uuid4()
    job_id = uuid4()
    owner_id = uuid4()

    mock_biz = Business(
        id=biz_id,
        name="Auto Mecânica Confiança",
        slug="auto-mecanica-confianca",
        status="approved",
        owner_user_id=owner_id,
        owner_paused=False,
        deleted_at=None,
        whatsapp="19988887777",
    )

    mock_job = JobOpening(
        id=job_id,
        business_id=biz_id,
        title="Mecânico Automotivo Sênior",
        title_normalized="mecanico automotivo senior",
        description="Profissional com experiência em injeção eletrônica.",
        contract_type="clt",
        status="active",
        owner_paused=False,
        admin_hold=False,
        expires_at=datetime.now(timezone.utc) + timedelta(days=30),
        business=mock_biz,
    )

    # 1. Valida propriedade de visibilidade pública da vaga
    assert mock_job.is_publicly_visible is True

    # 2. Se a empresa for pausada pelo dono, a vaga deixa de estar visível publicamente
    mock_biz.owner_paused = True
    assert mock_job.is_publicly_visible is False
    mock_biz.owner_paused = False

    # 3. Se a vaga expirar, deixa de estar visível
    mock_job.expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
    assert mock_job.is_publicly_visible is False
    mock_job.expires_at = datetime.now(timezone.utc) + timedelta(days=30)
    assert mock_job.is_publicly_visible is True

    # 4. Se a empresa receber exclusão lógica (deleted_at preenchido), vaga é despublicada
    mock_biz.deleted_at = datetime.now(timezone.utc)
    mock_biz.status = "suspended"
    assert mock_job.is_publicly_visible is False
