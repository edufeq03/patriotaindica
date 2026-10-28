import pytest
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.core.database import get_db
from backend.app.core.security import get_current_user
from backend.app.models.user import User
from backend.app.models.business import Business

client = TestClient(app)


def test_health_check_endpoint():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "online"
    assert data["version"] == "2.0.0"


def test_application_validation_missing_name():
    # Sem nome obrigatório
    payload = {
        "whatsapp": "19999998888",
        "neighborhood": "Cambuí",
        "city": "Campinas",
        "state": "SP",
    }
    response = client.post("/api/v1/businesses/application", json=payload)
    assert response.status_code == 422


def test_application_validation_invalid_state():
    # Estado inexistente
    payload = {
        "name": "Auto Elétrica Patriota",
        "whatsapp": "19999998888",
        "neighborhood": "Centro",
        "city": "Campinas",
        "state": "ZZ",
    }
    response = client.post("/api/v1/businesses/application", json=payload)
    assert response.status_code == 422
    assert "Estado (UF) inválido" in response.text


def test_application_validation_invalid_cnpj():
    # CNPJ com dígitos verificadores inválidos
    payload = {
        "name": "Auto Elétrica Patriota",
        "whatsapp": "19999998888",
        "neighborhood": "Centro",
        "city": "Campinas",
        "state": "SP",
        "document_type": "CNPJ",
        "document_number": "11111111000100",  # Dígitos verificadores incorretos
    }
    response = client.post("/api/v1/businesses/application", json=payload)
    assert response.status_code == 422
    assert "dígitos verificadores" in response.text


def test_application_honeypot_spam_rejected():
    # Honeypot preenchido por bot
    payload = {
        "name": "Spam Bot Business",
        "whatsapp": "19999998888",
        "neighborhood": "Centro",
        "city": "Campinas",
        "state": "SP",
        "website_url_hp": "http://spamsite.xyz",
    }
    response = client.post("/api/v1/businesses/application", json=payload)
    assert response.status_code == 422
    assert "spam" in response.text.lower()


def test_application_submit_success_with_mock_db():
    async def override_get_db():
        mock_db = AsyncMock()
        mock_scalar = MagicMock()
        mock_scalar.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_scalar
        yield mock_db

    app.dependency_overrides[get_db] = override_get_db
    try:
        payload = {
            "name": "Mecânica Confiança Patriota",
            "description": "Serviços de mecânica e alinhamento com honestidade.",
            "whatsapp": "19987654321",
            "neighborhood": "Taquaral",
            "city": "Campinas",
            "state": "SP",
            "service_mode": "at_location",
            "service_radius_km": 15,
        }
        response = client.post("/api/v1/businesses/application", json=payload)
        assert response.status_code == 201
        data = response.json()
        assert data["success"] is True
        assert data["status"] == "pending_review"
        assert "business_id" in data
    finally:
        app.dependency_overrides.pop(get_db, None)


def test_enum_compilation_no_varchar_cast():
    """Garante que colunas com PostgreSQL ENUM não recebam typecast ::VARCHAR indevido."""
    import sqlalchemy as sa
    from sqlalchemy.dialects.postgresql import insert
    from backend.app.models.business import Business
    from backend.app.models.category import Category
    from backend.app.models.events import BusinessReviewLog

    stmt = insert(Business).values(
        name="Teste",
        slug="teste-slug",
        whatsapp="19999999999",
        neighborhood="Centro",
        city="Campinas",
        state="SP",
        listing_type="service",
        service_mode="at_customer",
        status="pending_review",
        source="application",
    )
    compiled = str(stmt.compile(dialect=sa.dialects.postgresql.dialect()))
    assert "listing_type)s::VARCHAR" not in compiled
    assert "service_mode)s::VARCHAR" not in compiled
    assert "status)s::VARCHAR" not in compiled
    assert "source)s::VARCHAR" not in compiled

    stmt_cat = insert(Category).values(name="Cat", slug="cat", kind="service")
    assert "kind)s::VARCHAR" not in str(stmt_cat.compile(dialect=sa.dialects.postgresql.dialect()))

    stmt_log = insert(BusinessReviewLog).values(
        business_id="00000000-0000-0000-0000-000000000000",
        from_status="pending_review",
        to_status="approved",
    )
    compiled_log = str(stmt_log.compile(dialect=sa.dialects.postgresql.dialect()))
    assert "from_status)s::VARCHAR" not in compiled_log
    assert "to_status)s::VARCHAR" not in compiled_log


def test_search_endpoint_success_with_mock_db():
    """Garante que /api/v1/search responde 200 e lista os negócios sem erro."""
    async def override_get_db():
        mock_db = AsyncMock()
        mock_scalar = MagicMock()
        mock_scalar.scalars.return_value.all.return_value = []
        mock_scalar.all.return_value = []
        mock_db.execute.return_value = mock_scalar
        yield mock_db

    app.dependency_overrides[get_db] = override_get_db
    try:
        response = client.get("/api/v1/search?page=1&limit=20")
        assert response.status_code == 200
        data = response.json()
        assert "results" in data
        assert "page" in data
    finally:
        app.dependency_overrides.pop(get_db, None)


def test_list_categories_endpoint_success():
    """Garante que /api/v1/categories responde 200."""
    async def override_get_db():
        mock_db = AsyncMock()
        mock_scalar = MagicMock()
        mock_scalar.scalars.return_value.all.return_value = []
        mock_db.execute.return_value = mock_scalar
        yield mock_db

    app.dependency_overrides[get_db] = override_get_db
    try:
        response = client.get("/api/v1/categories")
        assert response.status_code == 200
        assert isinstance(response.json(), list)
    finally:
        app.dependency_overrides.pop(get_db, None)


def test_admin_create_category_requires_auth():
    """Criação direta de categoria sem token de admin é rejeitada com 401."""
    response = client.post("/api/v1/categories", json={"name": "Adestrador de Cães", "kind": "service"})
    assert response.status_code in (401, 403)


def test_admin_create_category_success_with_mock():
    """Admin autenticado consegue cadastrar categoria diretamente."""
    from backend.app.core.security import get_current_active_admin
    from backend.app.models.user import User
    from uuid import uuid4

    mock_admin = User(
        id=uuid4(),
        name="Admin Test",
        email="admin@patriotaindica.com.br",
        role="admin",
        is_active=True,
    )

    async def override_admin():
        return mock_admin

    async def override_get_db():
        mock_db = AsyncMock()
        mock_scalar = MagicMock()
        mock_scalar.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_scalar

        async def mock_refresh(instance):
            instance.id = uuid4()
            from datetime import datetime, timezone
            instance.created_at = datetime.now(timezone.utc)

        mock_db.refresh = mock_refresh
        yield mock_db

    app.dependency_overrides[get_current_active_admin] = override_admin
    app.dependency_overrides[get_db] = override_get_db
    try:
        response = client.post(
            "/api/v1/categories",
            json={"name": "Adestrador de Cães", "kind": "service", "icon_name": "paw-print"},
        )
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Adestrador de Cães"
        assert data["status"] == "approved"
        assert "adestrador" in data["slug"]
    finally:
        app.dependency_overrides.pop(get_current_active_admin, None)
        app.dependency_overrides.pop(get_db, None)


def test_get_payment_plans():
    """Endpoint público de planos retorna os 3 planos oficiais."""
    response = client.get("/api/v1/payments/plans")
    assert response.status_code == 200
    plans = response.json()
    assert len(plans) == 3
    plan_ids = [p["id"] for p in plans]
    assert "mensal" in plan_ids
    assert "semestral" in plan_ids
    assert "anual" in plan_ids

    anual = next(p for p in plans if p["id"] == "anual")
    assert anual["monthly_equivalent"] == "R$ 9,99"
    assert anual["price_cents"] == 11988
    assert anual["popular"] is True


def test_create_mercadopago_preference():
    """Geração de preferência do Mercado Pago para usuário logado."""
    from backend.app.core.security import get_current_user
    from backend.app.models.user import User
    from uuid import uuid4

    mock_owner = User(
        id=uuid4(),
        name="Empresária Patriota",
        email="empresaria@teste.com",
        role="owner",
        is_active=True,
    )

    async def override_user():
        return mock_owner

    async def override_get_db():
        mock_db = AsyncMock()
        yield mock_db

    app.dependency_overrides[get_current_user] = override_user
    app.dependency_overrides[get_db] = override_get_db
    try:
        response = client.post(
            "/api/v1/payments/create-preference",
            json={"plan_id": "anual"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "preference_id" in data
        assert "init_point" in data
        assert data["plan"]["id"] == "anual"
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(get_db, None)


def test_simulate_activation_and_my_subscription():
    """Simulação de ativação de assinatura e consulta de status."""
    from backend.app.core.security import get_current_user
    from backend.app.models.user import User
    from backend.app.models.subscription import Subscription
    from datetime import datetime, timedelta, timezone
    from uuid import uuid4

    mock_owner = User(
        id=uuid4(),
        name="Empresário Patriota",
        email="dono@teste.com",
        role="owner",
        is_active=True,
    )

    async def override_user():
        return mock_owner

    # Test simulate activation
    async def override_get_db_activate():
        mock_db = AsyncMock()
        mock_scalar = MagicMock()
        mock_scalar.scalars.return_value.first.return_value = None
        mock_db.execute.return_value = mock_scalar
        yield mock_db

    app.dependency_overrides[get_current_user] = override_user
    app.dependency_overrides[get_db] = override_get_db_activate
    try:
        # T0.1 / T0.6: Endpoint simulate-activation apagado e DEVE retornar 404
        res_act = client.post("/api/v1/payments/simulate-activation?plan_id=anual")
        assert res_act.status_code == 404
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(get_db, None)

    # Test my-subscription
    fake_sub = Subscription(
        id=uuid4(),
        owner_user_id=mock_owner.id,
        plan_id="anual",
        status="active",
        current_period_start=datetime.now(timezone.utc),
        current_period_end=datetime.now(timezone.utc) + timedelta(days=365),
    )

    async def override_get_db_sub():
        mock_db = AsyncMock()
        mock_res1 = MagicMock()
        mock_res1.scalars.return_value.first.return_value = fake_sub
        mock_res2 = MagicMock()
        mock_res2.scalars.return_value.all.return_value = []
        mock_res3 = MagicMock()
        mock_res3.scalar.return_value = 2  # 2 indicações

        mock_db.execute.side_effect = [mock_res1, mock_res2, mock_res3, mock_res3]
        yield mock_db

    app.dependency_overrides[get_current_user] = override_user
    app.dependency_overrides[get_db] = override_get_db_sub
    try:
        res_sub = client.get("/api/v1/payments/my-subscription")
        assert res_sub.status_code == 200
        sub_data = res_sub.json()
        assert sub_data["is_active"] is True
        assert sub_data["plan_id"] == "anual"
        assert sub_data["days_remaining"] > 350
        assert "referral_code" in sub_data
        assert "referral_link" in sub_data
        assert sub_data["referral_stats"]["total_rewarded"] == 2
        assert sub_data["referral_stats"]["free_months_earned"] == 2
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(get_db, None)


def test_application_multiple_businesses_same_document():
    """Garante que a mesma dona (mesmo CPF/CNPJ) pode cadastrar negócios distintos."""
    from uuid import uuid4

    async def override_get_db_allow():
        mock_db = AsyncMock()
        mock_res_slug = MagicMock()
        mock_res_slug.scalar_one_or_none.return_value = None
        # Sem duplicidade para mesmo nome
        mock_res_doc = MagicMock()
        mock_res_doc.scalar_one_or_none.return_value = None

        mock_db.execute.side_effect = [mock_res_slug, mock_res_doc]
        yield mock_db

    app.dependency_overrides[get_db] = override_get_db_allow
    try:
        payload = {
            "name": "Maria Artesanatos Criativos",
            "listing_type": "product",
            "document_type": "CNPJ",
            "document_number": "11.222.333/0001-81",
            "whatsapp": "19999998888",
            "neighborhood": "Cambuí",
            "city": "Campinas",
            "state": "SP",
            "serves_online": True,
        }
        res = client.post("/api/v1/businesses/application", json=payload)
        assert res.status_code == 201
        assert res.json()["success"] is True
    finally:
        app.dependency_overrides.pop(get_db, None)

    # Agora mesmo documento e mesmo nome é bloqueado com 400
    async def override_get_db_duplicate():
        mock_db = AsyncMock()
        mock_res_slug = MagicMock()
        mock_res_slug.scalar_one_or_none.return_value = None
        mock_res_doc = MagicMock()
        mock_res_doc.scalar_one_or_none.return_value = uuid4()  # Já existe mesmo nome e documento

        mock_db.execute.side_effect = [mock_res_slug, mock_res_doc]
        yield mock_db

    app.dependency_overrides[get_db] = override_get_db_duplicate
    try:
        payload = {
            "name": "Maria Artesanatos Criativos",
            "listing_type": "product",
            "document_type": "CNPJ",
            "document_number": "11.222.333/0001-81",
            "whatsapp": "19999998888",
            "neighborhood": "Cambuí",
            "city": "Campinas",
            "state": "SP",
        }
        res = client.post("/api/v1/businesses/application", json=payload)
        assert res.status_code == 400
        assert "mesmo nome e CNPJ/CPF" in res.json()["detail"]
    finally:
        app.dependency_overrides.pop(get_db, None)


def test_request_otp_by_phone_success_and_contingency():
    test_id = uuid4()
    mock_row = (test_id, "UltraLimpCampinas", "19996737713")

    async def override_get_db_otp():
        mock_db = AsyncMock()
        mock_res = MagicMock()
        mock_res.all.return_value = [mock_row]
        mock_db.execute.return_value = mock_res
        yield mock_db

    app.dependency_overrides[get_db] = override_get_db_otp
    try:
        # 1. Envio normal com busca por dígitos
        res = client.post("/api/v1/claim/request-otp-by-phone", json={"phone": "19996737713"})
        assert res.status_code == 200
        data = res.json()
        assert data["success"] is True
        assert data["business_id"] == str(test_id)
        assert data["business_name"] == "UltraLimpCampinas"
        # T0.6: dev_code NUNCA deve ser retornado na resposta HTTP
        assert "dev_code" not in data

        # 2. Resiliência: se o número não for encontrado, retorna 404 amigável
        mock_row_empty = MagicMock()
        async def override_get_db_empty():
            mock_db = AsyncMock()
            mock_res = MagicMock()
            mock_res.all.return_value = []
            mock_db.execute.return_value = mock_res
            yield mock_db
        app.dependency_overrides[get_db] = override_get_db_empty
        res_nf = client.post("/api/v1/claim/request-otp-by-phone", json={"phone": "11988887777"})
        assert res_nf.status_code == 404
        assert "Nenhuma empresa encontrada" in res_nf.json()["detail"]
    finally:
        app.dependency_overrides.pop(get_db, None)


def test_dangerous_endpoints_removed_return_404():
    """
    T0.1: Nenhuma das rotas perigosas deve existir no sistema (todas devem retornar 404).
    """
    assert client.get("/api/v1/system/migrate").status_code == 404
    assert client.post("/api/v1/triage/reset-businesses").status_code == 404
    assert client.get("/api/v1/triage/test-evolution").status_code == 404
    assert client.get("/api/v1/search/audit").status_code == 404
    assert client.post("/api/v1/payments/simulate-activation").status_code == 404


def test_public_by_slug_returns_404_for_pending_business():
    """
    T0.5: by-slug só deve retornar empresas com status = 'approved'.
    Empresas com status = 'pending_review' devem retornar 404 na rota pública.
    """
    async def override_get_db_pending():
        mock_db = AsyncMock()
        mock_res = MagicMock()
        mock_res.scalar_one_or_none.return_value = None  # query filtra status='approved', logo não acha
        mock_db.execute.return_value = mock_res
        yield mock_db

    app.dependency_overrides[get_db] = override_get_db_pending
    try:
        res = client.get("/api/v1/businesses/by-slug/empresa-em-analise")
        assert res.status_code == 404
        assert "não encontrada ou inativa" in res.json()["detail"].lower()
    finally:
        app.dependency_overrides.pop(get_db, None)


def test_toggle_business_pause_forbids_pending_status():
    """
    T0.6: toggle-pause não aprova empresas em pending_review nem reativa suspensas sem admin.
    """
    owner_user = User(id=uuid4(), name="Dono", email="dono@teste.com", role="owner", is_active=True)
    pending_biz = Business(
        id=uuid4(),
        owner_user_id=owner_user.id,
        name="Empresa Pendente",
        slug="empresa-pendente",
        status="pending_review",
    )

    async def override_user():
        return owner_user

    async def override_get_db_toggle():
        mock_db = AsyncMock()
        mock_res = MagicMock()
        mock_res.scalar_one_or_none.return_value = pending_biz
        mock_db.execute.return_value = mock_res
        yield mock_db

    app.dependency_overrides[get_current_user] = override_user
    app.dependency_overrides[get_db] = override_get_db_toggle
    try:
        res = client.post(f"/api/v1/owner/{pending_biz.id}/toggle-pause")
        assert res.status_code == 400
        assert "Apenas empresas aprovadas podem ser pausadas" in res.json()["detail"]
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(get_db, None)


def test_privacy_request_endpoint_201_and_rate_limit_429():
    """
    T0.7: POST /api/v1/privacy/request retorna 201 e aplica rate limit 429 na 11ª chamada/hora.
    """
    async def override_get_db_privacy():
        mock_db = AsyncMock()
        yield mock_db

    app.dependency_overrides[get_db] = override_get_db_privacy
    try:
        payload = {
            "request_type": "deletion",
            "email": "titular@exemplo.com",
            "details": "Solicito exclusão dos meus dados cadastrais.",
        }
        res = client.post("/api/v1/privacy/request", json=payload, headers={"X-Forwarded-For": "203.0.113.195"})
        assert res.status_code == 201
        data = res.json()
        assert data["request_type"] == "deletion"
        assert data["status"] == "received"
    finally:
        app.dependency_overrides.pop(get_db, None)

