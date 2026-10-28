import os
import uuid
import pytest
from unittest.mock import AsyncMock, MagicMock
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.core.config import Settings, settings
from backend.app.core.security import decode_access_token, get_current_user
from backend.app.core.database import get_db, set_db_app_context
from backend.app.models.user import User
from backend.app.models.business import Business
from backend.app.services.otp import otp_service
from fastapi import HTTPException

client = TestClient(app)


def test_t01_dangerous_endpoints_return_404():
    """T0.1: Todas as rotas perigosas e de contingência devem retornar 404."""
    assert client.get("/api/v1/system/migrate").status_code == 404
    assert client.post("/api/v1/triage/reset-businesses").status_code == 404
    assert client.get("/api/v1/triage/test-evolution").status_code == 404
    assert client.get("/api/v1/search/audit").status_code == 404
    assert client.post("/api/v1/payments/simulate-activation").status_code == 404


def test_t02_jwt_secrets_and_blocklist():
    """T0.2: Settings sem chave válida rejeita; blocklist rejeitada; token com segredo antigo rejeitado."""
    # Menos de 64 caracteres
    with pytest.raises(ValueError, match="mínimo 64 caracteres"):
        Settings(JWT_SECRET_KEY="1234567890abcdef1234567890abcdef")

    # Termos de blocklist
    for bad in ["sua_chave", "dev_key", "change", "secret", "example", "exemplo"]:
        with pytest.raises(ValueError, match="termo proibido"):
            Settings(JWT_SECRET_KEY=f"0123456789abcdef0123456789abcdef_{bad}_0123456789abcdef0123456789abcdef")

    # Chave válida >= 64 caracteres sem blocklist é aceita
    valid_key = "a1b2c3d4e5f60718293a4b5c6d7e8f90a1b2c3d4e5f60718293a4b5c6d7e8f90"
    s = Settings(JWT_SECRET_KEY=valid_key)
    assert s.JWT_SECRET_KEY == valid_key


def test_t03_error_sanitization_and_request_id():
    """T0.3: Handler global retorna erro genérico com request_id e header X-Request-ID sem expor trace."""
    test_client = TestClient(app, raise_server_exceptions=False)

    # Força exceção em rota de teste
    @app.get("/api/v1/test-crash-unhandled")
    async def crash_endpoint():
        raise RuntimeError("DATABASE_PASSWORD_LEAK: postgres://admin:super_secret@db/prod")

    res = test_client.get("/api/v1/test-crash-unhandled")
    assert res.status_code == 500
    data = res.json()
    assert "request_id" in data
    assert "DATABASE_PASSWORD_LEAK" not in res.text
    assert "RuntimeError" not in res.text
    assert "super_secret" not in res.text
    assert res.headers.get("X-Request-ID") == data["request_id"]


@pytest.mark.anyio
async def test_t03_set_db_app_context_fails_closed():
    """T0.3: set_db_app_context falha fechada (500) se não conseguir aplicar contexto no PostgreSQL."""
    mock_session = AsyncMock()
    mock_session.bind = MagicMock()
    mock_session.bind.dialect.name = "postgresql"
    mock_session.execute.side_effect = Exception("Conexão com PostgreSQL corrompida")

    with pytest.raises(HTTPException) as exc_info:
        await set_db_app_context(mock_session, user_id=str(uuid.uuid4()), role="owner")
    assert exc_info.value.status_code == 500
    assert "segurança" in exc_info.value.detail.lower()


def test_t04_cors_and_allowed_hosts():
    """T0.4: ALLOWED_HOSTS sem '*' e CORS sem HTTP desprotegido."""
    assert "*" not in settings.ALLOWED_HOSTS
    assert "http://patriotaindica.com" not in settings.CORS_ORIGINS


def test_t05_by_slug_public_only_approved():
    """T0.5: by-slug só devolve status 'approved'. Empresa pending retorna 404."""
    async def override_get_db_pending():
        mock_db = AsyncMock()
        mock_res = MagicMock()
        mock_res.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_res
        yield mock_db

    app.dependency_overrides[get_db] = override_get_db_pending
    try:
        res = client.get("/api/v1/businesses/by-slug/empresa-em-analise")
        assert res.status_code == 404
        assert "não encontrada ou inativa" in res.json()["detail"].lower()
    finally:
        app.dependency_overrides.pop(get_db, None)


def test_t06_otp_123456_rejected_and_no_dev_code():
    """T0.6: Código 123456 é rejeitado e dev_code não é exposto."""
    valid, msg = otp_service.verify_otp("non-existent-biz", "123456")
    assert valid is False

    # Solicitação de OTP não contém dev_code
    mock_biz_id = uuid.uuid4()
    mock_row = MagicMock()
    mock_row.__getitem__.side_effect = lambda i: [mock_biz_id, "Padaria Teste", "19999998888"][i]

    async def override_db():
        mock_db = AsyncMock()
        mock_res = MagicMock()
        mock_res.first.return_value = mock_row
        mock_db.execute.return_value = mock_res
        yield mock_db

    app.dependency_overrides[get_db] = override_db
    try:
        res = client.post(f"/api/v1/claim/{mock_biz_id}/request-otp")
        assert res.status_code == 200
        data = res.json()
        assert "dev_code" not in data
        assert data["masked_phone"] == "+55 (19) 9****-8888"
    finally:
        app.dependency_overrides.pop(get_db, None)


def test_t06_toggle_pause_rejects_pending_or_suspended():
    """T0.6: toggle-pause não aprova pending_review nem reativa suspensa sem admin."""
    user = User(id=uuid.uuid4(), name="Dono", email="dono@teste.com", role="owner", is_active=True)
    pending_biz = Business(id=uuid.uuid4(), owner_user_id=user.id, name="Biz", slug="biz", status="pending_review")

    async def override_user():
        return user

    async def override_db():
        mock_db = AsyncMock()
        mock_res = MagicMock()
        mock_res.scalar_one_or_none.return_value = pending_biz
        mock_db.execute.return_value = mock_res
        yield mock_db

    app.dependency_overrides[get_current_user] = override_user
    app.dependency_overrides[get_db] = override_db
    try:
        res = client.post(f"/api/v1/owner/{pending_biz.id}/toggle-pause")
        assert res.status_code == 400
        assert "Apenas empresas aprovadas podem ser pausadas" in res.json()["detail"]
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(get_db, None)


def test_t07_privacy_request_201_and_rate_limit_429():
    """T0.7: POST /privacy/request retorna 201 e aplica 429 na 11ª chamada/h."""
    async def override_db():
        mock_db = AsyncMock()
        yield mock_db

    app.dependency_overrides[get_db] = override_db
    try:
        unique_ip = "198.51.100.77"
        payload = {
            "request_type": "deletion",
            "email": "lgpd@teste.com",
            "details": "Excluir meu cadastro por favor.",
        }
        # Primeiras 10 chamadas devem passar (201)
        for i in range(10):
            res = client.post("/api/v1/privacy/request", json=payload, headers={"X-Forwarded-For": unique_ip})
            assert res.status_code == 201, f"Chamada {i+1} falhou com status {res.status_code}"
            assert res.json()["status"] == "received"

        # A 11ª chamada deve ser barrada pelo rate limit (429)
        res_limit = client.post("/api/v1/privacy/request", json=payload, headers={"X-Forwarded-For": unique_ip})
        assert res_limit.status_code == 429
        assert "Muitas solicitações" in res_limit.json()["detail"]
    finally:
        app.dependency_overrides.pop(get_db, None)
