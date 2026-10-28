import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.core.database import get_db
from backend.app.core.security import get_current_user
from backend.app.models.business import Business, PeerEndorsement
from backend.app.models.user import User

client = TestClient(app)


@pytest.fixture
def mock_owner_user():
    return User(
        id=uuid4(),
        email="empresario@patriotaindica.internal",
        name="Empresário Patriota",
        role="owner",
        is_active=True,
    )


@pytest.fixture
def mock_approved_business(mock_owner_user):
    biz_id = uuid4()
    return Business(
        id=biz_id,
        owner_user_id=mock_owner_user.id,
        name="Oficina Patriota",
        slug="oficina-patriota",
        status="approved",
        owner_paused=False,
        whatsapp="19999998888",
        whatsapp_e164="+5519999998888",
        neighborhood="Cambuí",
        city="Campinas",
        state="SP",
        network_badge="membro_verificado",
        endorsements_count=0,
        availability_until=None,
    )


@pytest.fixture
def mock_target_business():
    target_id = uuid4()
    return Business(
        id=target_id,
        owner_user_id=uuid4(),
        name="Autopeças Brasil",
        slug="autopecas-brasil",
        status="approved",
        owner_paused=False,
        whatsapp="19988887777",
        whatsapp_e164="+5519988887777",
        neighborhood="Centro",
        city="Campinas",
        state="SP",
        network_badge="membro_verificado",
        endorsements_count=0,
        availability_until=None,
    )


# ==============================================================================
# T7.1: Selo "Disponível Agora" / Plantão Imediato
# ==============================================================================

@pytest.mark.anyio
async def test_t7_1_availability_toggle(mock_owner_user, mock_approved_business):
    app.dependency_overrides[get_current_user] = lambda: mock_owner_user
    mock_db = AsyncMock()

    mock_res = MagicMock()
    mock_res.scalar_one_or_none.return_value = mock_approved_business
    mock_db.execute.return_value = mock_res

    async def override_get_db():
        yield mock_db

    app.dependency_overrides[get_db] = override_get_db

    try:
        # 1. Ativar por 4 horas
        resp = client.post(
            f"/api/v1/owner/{mock_approved_business.id}/availability",
            json={"hours": 4},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["is_available_now"] is True
        assert data["remaining_hours"] == 4
        assert mock_approved_business.availability_until is not None

        # 2. Desativar (hours = 0)
        resp_off = client.post(
            f"/api/v1/owner/{mock_approved_business.id}/availability",
            json={"hours": 0},
        )
        assert resp_off.status_code == 200
        data_off = resp_off.json()
        assert data_off["is_available_now"] is False
        assert mock_approved_business.availability_until is None
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(get_db, None)


# ==============================================================================
# T7.2: Endossos e Recomendações Mútuas Entre Pares
# ==============================================================================

@pytest.mark.anyio
async def test_t7_2_peer_endorsements_flow(mock_owner_user, mock_approved_business, mock_target_business):
    app.dependency_overrides[get_current_user] = lambda: mock_owner_user
    mock_db = AsyncMock()

    async def override_get_db():
        yield mock_db

    app.dependency_overrides[get_db] = override_get_db

    try:
        # A. Bloqueio de Auto-Recomendação
        resp_self = client.post(
            f"/api/v1/owner/{mock_approved_business.id}/endorsements",
            json={"target_business_id": str(mock_approved_business.id), "relationship_type": "peer"},
        )
        assert resp_self.status_code == 400
        assert "não pode recomendar a si própria" in resp_self.json()["detail"]

        # B. Criação de Recomendação Confiável
        # Configurar retornos do mock de DB
        mock_res_src = MagicMock()
        mock_res_src.scalar_one_or_none.return_value = mock_approved_business

        mock_res_tgt = MagicMock()
        mock_res_tgt.scalar_one_or_none.return_value = mock_target_business

        mock_res_exist = MagicMock()
        mock_res_exist.scalar_one_or_none.return_value = None

        mock_res_count = MagicMock()
        mock_res_count.scalar.return_value = 1

        mock_db.execute.side_effect = [
            mock_res_src,
            mock_res_tgt,
            mock_res_exist,
            mock_res_count,
        ]

        resp_create = client.post(
            f"/api/v1/owner/{mock_approved_business.id}/endorsements",
            json={
                "target_business_id": str(mock_target_business.id),
                "relationship_type": "partner",
                "testimonial": "Excelente parceiro de peças mecânicas, entrega pontual e produtos de alta qualidade.",
            },
        )
        assert resp_create.status_code == 200
        data_create = resp_create.json()
        assert data_create["success"] is True
        assert data_create["endorsed_business_name"] == mock_target_business.name
        assert data_create["relationship_type"] == "partner"
        assert mock_target_business.endorsements_count == 1

        # C. Consulta Pública de Endossos (/businesses/by-slug/{slug}/endorsements)
        mock_endorsement = PeerEndorsement(
            id=uuid4(),
            endorsing_business_id=mock_approved_business.id,
            endorsed_business_id=mock_target_business.id,
            relationship_type="partner",
            testimonial="Excelente parceiro de peças mecânicas.",
            is_public=True,
            created_at=datetime.now(timezone.utc),
        )

        mock_res_biz = MagicMock()
        mock_res_biz.scalar_one_or_none.return_value = mock_target_business

        mock_res_all = MagicMock()
        mock_res_all.all.return_value = [(mock_endorsement, mock_approved_business)]

        mock_db.execute.side_effect = [mock_res_biz, mock_res_all]

        resp_get = client.get(f"/api/v1/businesses/by-slug/{mock_target_business.slug}/endorsements")
        assert resp_get.status_code == 200
        data_get = resp_get.json()
        assert data_get["endorsements_count"] == 1
        assert data_get["endorsements"][0]["endorsing_business_name"] == mock_approved_business.name
        assert data_get["endorsements"][0]["relationship_type"] == "partner"

    finally:
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(get_db, None)


# ==============================================================================
# T7.3: Cartão Digital de Confiança / Mini-site (/q/{slug})
# ==============================================================================

@pytest.mark.anyio
async def test_t7_3_trust_card_data(mock_approved_business):
    mock_db = AsyncMock()
    mock_res = MagicMock()
    mock_res.scalar_one_or_none.return_value = mock_approved_business
    mock_db.execute.return_value = mock_res

    async def override_get_db():
        yield mock_db

    app.dependency_overrides[get_db] = override_get_db

    try:
        resp = client.get(f"/api/v1/businesses/by-slug/{mock_approved_business.slug}/trust-card")
        assert resp.status_code == 200
        card = resp.json()
        assert card["name"] == mock_approved_business.name
        assert card["network_badge"] == "membro_verificado"
        assert "wa.me/5519999998888" in card["direct_whatsapp_url"]
        assert "Rede%20Patriota%20Indica" in card["direct_whatsapp_url"]
        assert f"/q/{mock_approved_business.slug}" in card["share_url"]
        assert "confi" in card["verified_network_statement"].lower()
    finally:
        app.dependency_overrides.pop(get_db, None)


# ==============================================================================
# T7.4: Auditoria de Segurança OWASP ASVS Nível 1
# ==============================================================================

def test_t7_4_owasp_asvs_audit_script():
    from scripts.audit_security_asvs import run_asvs_audit
    success = run_asvs_audit()
    assert success is True, "A auditoria OWASP ASVS Nível 1 deve passar com 100% de conformidade."
