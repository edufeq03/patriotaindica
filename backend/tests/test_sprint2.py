from datetime import datetime, timezone
import uuid
from unittest.mock import AsyncMock, MagicMock, patch
import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from backend.app.core.config import settings
from backend.app.core.rate_limit import check_rate_limit, get_client_ip
from backend.app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_access_token,
    decode_refresh_token,
    get_password_hash,
)
from backend.app.main import app
from backend.app.models.user import User


@pytest.fixture
def test_client():
    return TestClient(app)


def test_t2_1_token_generation_and_type_isolation():
    """
    T2.1: Valida que access_token e refresh_token têm tipos isolados
    e que um refresh_token não pode ser aceito como access_token.
    """
    user_id = str(uuid.uuid4())
    access_tok = create_access_token(subject=user_id, role="owner")
    refresh_tok, jti, ttl = create_refresh_token(subject=user_id, role="owner")

    # Access token decodifica com sucesso como access
    payload_access = decode_access_token(access_tok)
    assert payload_access is not None
    assert payload_access["sub"] == user_id
    assert payload_access["type"] == "access"

    # Refresh token decodifica como refresh
    payload_refresh = decode_refresh_token(refresh_tok)
    assert payload_refresh is not None
    assert payload_refresh["sub"] == user_id
    assert payload_refresh["type"] == "refresh"
    assert payload_refresh["jti"] == jti

    # ISOLAMENTO: decode_access_token DEVE rejeitar o refresh_token
    assert decode_access_token(refresh_tok) is None
    # decode_refresh_token DEVE rejeitar o access_token
    assert decode_refresh_token(access_tok) is None


@pytest.mark.anyio
async def test_t2_1_login_issues_access_and_refresh_tokens(test_client):
    """
    T2.1: Login bem-sucedido retorna par rotativo (access_token + refresh_token).
    """
    from backend.app.core.database import get_db

    user_id = uuid.uuid4()
    mock_user = User(
        id=user_id,
        name="Admin Teste",
        email="admin.sprint2@patriotaindica.com.br",
        password_hash=get_password_hash("SenhaForte123!"),
        role="admin",
        is_active=True,
        created_at=datetime.now(timezone.utc),
    )

    async def override_db():
        mock_res = MagicMock()
        mock_res.scalar_one_or_none.return_value = mock_user
        mock_db = AsyncMock()
        mock_db.execute.return_value = mock_res
        yield mock_db

    app.dependency_overrides[get_db] = override_db
    try:
        with patch("backend.app.api.v1.endpoints.auth.store_refresh_token", new_callable=AsyncMock) as mock_store:
            mock_store.return_value = True

            response = test_client.post(
                "/api/v1/auth/login",
                data={
                    "username": "admin.sprint2@patriotaindica.com.br",
                    "password": "SenhaForte123!",
                },
            )

            assert response.status_code == 200, response.text
            data = response.json()
            assert "access_token" in data
            assert "refresh_token" in data
            assert data["token_type"] == "bearer"
            assert data["user"]["email"] == "admin.sprint2@patriotaindica.com.br"
            mock_store.assert_awaited_once()
    finally:
        app.dependency_overrides.pop(get_db, None)


@pytest.mark.anyio
async def test_t2_1_refresh_token_rotation_and_replay_protection(test_client):
    """
    T2.1: Rotação atômica de refresh token e proteção contra reuso (replay attack).
    """
    from backend.app.core.database import get_db

    user_id = uuid.uuid4()
    mock_user = User(
        id=user_id,
        name="Gestor Teste",
        email="gestor@patriotaindica.com.br",
        role="owner",
        is_active=True,
        created_at=datetime.now(timezone.utc),
    )

    refresh_tok, jti, ttl = create_refresh_token(subject=user_id, role="owner")

    async def override_db():
        mock_res = MagicMock()
        mock_res.scalar_one_or_none.return_value = mock_user
        mock_db = AsyncMock()
        mock_db.execute.return_value = mock_res
        yield mock_db

    app.dependency_overrides[get_db] = override_db
    try:
        with patch("backend.app.api.v1.endpoints.auth.verify_and_revoke_refresh_token", new_callable=AsyncMock) as mock_verify, \
             patch("backend.app.api.v1.endpoints.auth.store_refresh_token", new_callable=AsyncMock) as mock_store:

            # 1ª tentativa: Token válido no Redis
            mock_verify.return_value = True
            mock_store.return_value = True

            response = test_client.post(
                "/api/v1/auth/refresh",
                json={"refresh_token": refresh_tok},
            )
            assert response.status_code == 200, response.text
            res_data = response.json()
            assert "access_token" in res_data
            assert "refresh_token" in res_data
            assert res_data["refresh_token"] != refresh_tok

            # 2ª tentativa (Replay attack): Token já consumido/inexistente no Redis
            mock_verify.return_value = False
            reused_response = test_client.post(
                "/api/v1/auth/refresh",
                json={"refresh_token": refresh_tok},
            )
            assert reused_response.status_code == 401
            assert "revogada ou refresh token já utilizado" in reused_response.json()["detail"]
    finally:
        app.dependency_overrides.pop(get_db, None)


@pytest.mark.anyio
async def test_t2_1_logout_endpoint_revokes_token(test_client):
    """
    T2.1: Endpoint /logout revoga o jti do refresh token no Redis.
    """
    refresh_tok, jti, ttl = create_refresh_token(subject="user_123", role="user")

    with patch("backend.app.api.v1.endpoints.auth.revoke_refresh_token", new_callable=AsyncMock) as mock_revoke:
        mock_revoke.return_value = True

        response = test_client.post(
            "/api/v1/auth/logout",
            json={"refresh_token": refresh_tok},
        )
        assert response.status_code == 200
        mock_revoke.assert_awaited_once_with(jti)


def test_t2_3_get_client_ip_priorities():
    """
    T2.3: Valida detecção confiável de IP e proteção contra spoofing em X-Forwarded-For.
    """
    from unittest.mock import MagicMock

    # 1. Cloudflare header tem prioridade máxima
    req_cf = MagicMock()
    req_cf.headers = {
        "CF-Connecting-IP": "200.100.50.25",
        "X-Forwarded-For": "10.0.0.1, 10.0.0.2",
    }
    assert get_client_ip(req_cf) == "200.100.50.25"

    # 2. X-Forwarded-For com spoofed IP à esquerda ("1.1.1.1, 189.40.10.5")
    # Com TRUSTED_PROXY_HOPS = 1, o IP real verificado pelo proxy de borda é 189.40.10.5
    req_proxy = MagicMock()
    req_proxy.headers = {
        "X-Forwarded-For": "1.1.1.1, 189.40.10.5",
    }
    assert get_client_ip(req_proxy) == "189.40.10.5"

    # 3. Fallback para client.host
    req_direct = MagicMock()
    req_direct.headers = {}
    req_direct.client.host = "192.168.1.100"
    assert get_client_ip(req_direct) == "192.168.1.100"


@pytest.mark.anyio
async def test_t2_3_rate_limit_fail_closed_behavior():
    """
    T2.3: Quando fail_closed=True e ENVIRONMENT=production, falha no Redis acarreta HTTP 503.
    """
    with patch("backend.app.core.rate_limit.atomic_rate_limit", side_effect=ConnectionError("Redis down")), \
         patch.object(settings, "ENVIRONMENT", "production"):
        with pytest.raises(HTTPException) as exc_info:
            await check_rate_limit(
                key="ratelimit:test_critical",
                limit=5,
                window_seconds=60,
                fail_closed=True,
            )
        assert exc_info.value.status_code == 503
