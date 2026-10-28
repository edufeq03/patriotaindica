import pytest
from unittest.mock import AsyncMock, MagicMock
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.core.database import get_db

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




