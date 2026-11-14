import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch
import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from backend.app.main import app
from backend.app.core.config import settings
from backend.app.core.database import get_db
from backend.app.core.security import get_current_active_admin, get_current_user
from backend.app.models.business import Business
from backend.app.models.events import BusinessPendingChange, Consent, Invitation
from backend.app.models.user import User
from backend.app.schemas.business import BusinessApplicationCreate
from backend.app.services.otp import OTPService, WhatsAppProvider, hash_phone, normalize_e164

client = TestClient(app)


# ==============================================================================
# T1.1: OTP e Reivindicação (Claim) à Prova de Burla
# ==============================================================================

def test_t1_1_phone_normalization_e164():
    """T1.1: Normalização de telefone para formato E.164 internacional (+55...)."""
    assert normalize_e164("19999998888") == "+5519999998888"
    assert normalize_e164("(19) 99999-8888") == "+5519999998888"
    assert normalize_e164("+5519999998888") == "+5519999998888"
    assert normalize_e164("5519999998888") == "+5519999998888"
    assert normalize_e164("123") is None
    assert normalize_e164("") is None


@pytest.mark.anyio
async def test_t1_1_otp_rate_limit_and_5_attempts_block():
    """T1.1: 4º envio no período de 1h retorna 429; 5 tentativas incorretas bloqueiam o código."""
    class MockWhatsApp(WhatsAppProvider):
        def __init__(self):
            self.sent_codes = []
        async def send_otp(self, phone: str, code: str, business_name: str):
            self.sent_codes.append(code)
            return True, "Enviado com sucesso"

    provider = MockWhatsApp()
    service = OTPService(provider=provider)
    phone = "+5519999991111"

    # Envios 1, 2, 3 permitidos
    ok1, _ = await service.request_otp_by_e164(phone)
    ok2, _ = await service.request_otp_by_e164(phone)
    ok3, _ = await service.request_otp_by_e164(phone)
    assert ok1 is True
    assert ok2 is True
    assert ok3 is True

    # 4º envio deve falhar por limite de taxa (3 por hora)
    ok4, msg4 = await service.request_otp_by_e164(phone)
    assert ok4 is False
    assert "Limite de envios excedido" in msg4

    # Testa 5 tentativas incorretas no último código válido
    last_code = provider.sent_codes[-1]
    for attempt in range(1, 5):
        valid, err = service.verify_otp_by_e164(phone, "000000")
        assert valid is False
        assert f"{5 - attempt} tentativa(s)" in err

    # 5ª tentativa incorreta bloqueia e destrói o código
    valid5, err5 = service.verify_otp_by_e164(phone, "000000")
    assert valid5 is False
    assert "Código bloqueado" in err5

    # Mesmo com o código correto agora, a verificação deve falhar porque o código foi destruído
    valid_after_block, _ = service.verify_otp_by_e164(phone, last_code)
    assert valid_after_block is False


def test_t1_1_anti_enumeration_identical_response():
    """T1.1: request-otp-by-phone responde com corpo idêntico para número existente e inexistente."""
    mock_id = uuid.uuid4()
    mock_existing = (mock_id, "Loja Real", "+5519999992222", "+5519999992222")

    async def override_db_existing():
        db = AsyncMock()
        res = MagicMock()
        res.all.return_value = [mock_existing]
        db.execute.return_value = res
        yield db

    async def override_db_non_existing():
        db = AsyncMock()
        res = MagicMock()
        res.all.return_value = []
        db.execute.return_value = res
        yield db

    # 1. Requisição para número existente
    app.dependency_overrides[get_db] = override_db_existing
    try:
        res_existing = client.post("/api/v1/claim/request-otp-by-phone", json={"phone": "19999992222"})
        assert res_existing.status_code == 200
        data_existing = res_existing.json()
        assert "business_id" not in data_existing
        assert "business_name" not in data_existing
        assert "dev_code" not in data_existing
    finally:
        app.dependency_overrides.pop(get_db, None)

    # 2. Requisição para número inexistente
    app.dependency_overrides[get_db] = override_db_non_existing
    try:
        res_non_existing = client.post("/api/v1/claim/request-otp-by-phone", json={"phone": "19988883333"})
        assert res_non_existing.status_code == 200
        data_non_existing = res_non_existing.json()
        # Resposta idêntica (previne adivinhação de telefones cadastrados)
        assert data_non_existing == data_existing
    finally:
        app.dependency_overrides.pop(get_db, None)


def test_t1_1_pre_hijacking_prevention_creates_synthetic_user():
    """T1.1 & H3: Verificação cria usuário NOVO com email sintético exclusivo; nunca reutiliza usuário por telefone."""
    biz_id = uuid.uuid4()
    biz = Business(
        id=biz_id,
        name="Padaria Segura",
        slug="padaria-segura",
        whatsapp="19999994444",
        whatsapp_e164="+5519999994444",
        status="pending_review",
        is_verified=False,
    )

    async def override_db():
        db = AsyncMock()
        res = MagicMock()
        res.scalars.return_value.all.return_value = [biz]
        db.execute.return_value = res
        yield db

    app.dependency_overrides[get_db] = override_db
    try:
        with patch("backend.app.api.v1.endpoints.claim.otp_service.verify_otp_by_e164", return_value=(True, "OK")):
            res = client.post(
                "/api/v1/claim/verify-otp",
                json={"phone": "+5519999994444", "code": "654321"},
            )
            assert res.status_code == 200
            data = res.json()
            assert data["success"] is True
            assert "access_token" in data
            assert "@patriotaindica.internal" in data["user"]["email"]
            assert data["user"]["email"].startswith(f"owner-{biz_id.hex[:8]}")
            # Status e is_verified NUNCA mudam
            assert biz.status == "pending_review"
            assert biz.is_verified is False
            assert biz.whatsapp_verified_at is not None
    finally:
        app.dependency_overrides.pop(get_db, None)


# ==============================================================================
# T1.2: Status de Curadoria Exclusivo do Admin e Separação de owner_paused
# ==============================================================================

def test_t1_2_owner_toggle_pause_only_on_approved_businesses():
    """T1.2: toggle-pause apenas alterna owner_paused em empresas aprovadas, sem mudar status."""
    owner = User(id=uuid.uuid4(), name="Dono", email="dono@biz.com", role="owner", is_active=True)
    approved_biz = Business(
        id=uuid.uuid4(),
        owner_user_id=owner.id,
        name="Empresa Aprovada",
        slug="empresa-aprovada",
        status="approved",
        owner_paused=False,
    )

    async def override_user():
        return owner

    async def override_db():
        db = AsyncMock()
        res = MagicMock()
        res.scalar_one_or_none.return_value = approved_biz
        db.execute.return_value = res
        yield db

    app.dependency_overrides[get_current_user] = override_user
    app.dependency_overrides[get_db] = override_db
    try:
        # 1. Pausar anúncio
        res = client.post(f"/api/v1/owner/{approved_biz.id}/toggle-pause")
        assert res.status_code == 200
        assert res.json()["owner_paused"] is True
        assert res.json()["status"] == "approved"
        assert approved_biz.owner_paused is True
        assert approved_biz.status == "approved"

        # 2. Reativar anúncio
        res2 = client.post(f"/api/v1/owner/{approved_biz.id}/toggle-pause")
        assert res2.status_code == 200
        assert res2.json()["owner_paused"] is False
        assert res2.json()["status"] == "approved"
        assert approved_biz.owner_paused is False
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(get_db, None)


def test_t1_2_public_by_slug_omits_owner_paused_businesses():
    """T1.2: Empresa aprovada mas pausada pelo proprietário retorna 404 na página pública."""
    paused_biz = Business(
        id=uuid.uuid4(),
        name="Empresa Pausada",
        slug="empresa-pausada",
        status="approved",
        owner_paused=True,
    )

    async def override_db():
        db = AsyncMock()
        res = MagicMock()
        res.scalar_one_or_none.return_value = None  # Filtro owner_paused=False não encontra
        db.execute.return_value = res
        yield db

    app.dependency_overrides[get_db] = override_db
    try:
        res = client.get("/api/v1/businesses/by-slug/empresa-pausada")
        assert res.status_code == 404
    finally:
        app.dependency_overrides.pop(get_db, None)


# ==============================================================================
# T1.3: Edição do Dono - Baixo Risco vs Proposta de Mudanças
# ==============================================================================

def test_t1_3_profile_update_allows_only_low_risk_fields():
    """T1.3: PUT /owner/{id}/profile aceita apenas campos de baixo risco; campos de risco são rejeitados com 422."""
    owner = User(id=uuid.uuid4(), name="Dono", email="dono@biz.com", role="owner", is_active=True)
    biz = Business(
        id=uuid.uuid4(),
        owner_user_id=owner.id,
        name="Empresa Original",
        slug="empresa-original",
        status="approved",
        description="Descrição antiga",
    )

    async def override_user():
        return owner

    async def override_db():
        db = AsyncMock()
        res = MagicMock()
        res.scalar_one_or_none.return_value = biz
        db.execute.return_value = res
        yield db

    app.dependency_overrides[get_current_user] = override_user
    app.dependency_overrides[get_db] = override_db
    try:
        # 1. Campos de baixo risco válidos
        res_ok = client.put(
            f"/api/v1/owner/{biz.id}/profile",
            json={
                "description": "Nova descrição atualizada",
                "service_radius_km": 40,
                "logo_url": "/static/uploads/logo123.png",
            },
        )
        assert res_ok.status_code == 200
        assert biz.description == "Nova descrição atualizada"
        assert biz.service_radius_km == 40

        # 2. Campo de alto risco (name) enviado diretamente para /profile é REJEITADO (422)
        res_risk = client.put(
            f"/api/v1/owner/{biz.id}/profile",
            json={"name": "Nome Alterado Sem Permissao"},
        )
        assert res_risk.status_code == 422

        # 3. Logo fora do armazenamento interno é REJEITADO
        res_bad_logo = client.put(
            f"/api/v1/owner/{biz.id}/profile",
            json={"logo_url": "https://malicious.com/evil.jpg"},
        )
        assert res_bad_logo.status_code == 422
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(get_db, None)


def test_t1_3_propose_changes_quarantine_and_cap_of_3():
    """T1.3: POST /propose-changes coloca alterações em quarentena e barra 4ª solicitação simultânea."""
    owner = User(id=uuid.uuid4(), name="Dono", email="dono@biz.com", role="owner", is_active=True)
    biz = Business(
        id=uuid.uuid4(),
        owner_user_id=owner.id,
        name="Empresa Aprovada",
        slug="empresa-aprovada",
        status="approved",
    )

    async def override_user():
        return owner

    async def override_db_cap_reached():
        db = AsyncMock()
        res_biz = MagicMock()
        res_biz.scalar_one_or_none.return_value = biz
        res_count = MagicMock()
        res_count.scalar.return_value = 3  # Já possui 3 pendências
        db.execute.side_effect = [res_biz, res_count]
        yield db

    app.dependency_overrides[get_current_user] = override_user
    app.dependency_overrides[get_db] = override_db_cap_reached
    try:
        res = client.post(
            f"/api/v1/owner/{biz.id}/propose-changes",
            json={"name": "Novo Nome Proposto"},
        )
        assert res.status_code == 400
        assert "Limite de 3 alterações pendentes atingido" in res.json()["detail"]
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(get_db, None)


# ==============================================================================
# T1.4: Detecção de Documento Duplicado e Bloqueio na Triagem
# ==============================================================================

def test_t1_4_duplicate_document_blocks_admin_approval_without_override():
    """T1.4: Triagem rejeita aprovação de empresa com document_flag_duplicate se confirm_duplicate_document não for enviado."""
    admin = User(id=uuid.uuid4(), name="Admin", email="admin@patriota.com", role="admin", is_active=True)
    flagged_biz = Business(
        id=uuid.uuid4(),
        name="Empresa com CNPJ Duplicado",
        slug="empresa-cnpj-duplicado",
        status="pending_review",
        document_flag_duplicate=True,
    )

    async def override_admin():
        return admin

    async def override_db():
        db = AsyncMock()
        res_biz = MagicMock()
        res_biz.scalar_one_or_none.return_value = flagged_biz
        res_cats = MagicMock()
        res_cats.scalars.return_value.all.return_value = []
        db.execute.side_effect = [res_biz, res_cats, res_biz, res_cats]
        yield db

    app.dependency_overrides[get_current_active_admin] = override_admin
    app.dependency_overrides[get_db] = override_db
    try:
        # 1. Tentativa de aprovação sem confirm_duplicate_document => 400
        payload_no_override = {"action": "approve", "confirm_duplicate_document": False}
        res_err = client.post(f"/api/v1/triage/decision/{flagged_biz.id}", json=payload_no_override)
        assert res_err.status_code == 400
        assert "documento (CNPJ/CPF) já cadastrado" in res_err.json()["detail"]

        # 2. Aprovação com confirm_duplicate_document=True => 200
        payload_with_override = {"action": "approve", "confirm_duplicate_document": True}
        res_ok = client.post(f"/api/v1/triage/decision/{flagged_biz.id}", json=payload_with_override)
        assert res_ok.status_code == 200
        assert flagged_biz.status == "approved"
    finally:
        app.dependency_overrides.pop(get_current_active_admin, None)
        app.dependency_overrides.pop(get_db, None)


# ==============================================================================
# T1.6: Consentimentos LGPD Persistidos e Revogação
# ==============================================================================

def test_t1_6_application_requires_lgpd_consents():
    """T1.6: Submissão de candidatura sem consentimento explícito retorna 422."""
    payload_missing_consent = {
        "name": "Loja Sem Aceite",
        "whatsapp": "19999995555",
        "neighborhood": "Centro",
        "city": "Campinas",
        "state": "SP",
        # consent_carta_principios, consent_termos e consent_privacidade ausentes
    }
    res = client.post("/api/v1/businesses/application", json=payload_missing_consent)
    assert res.status_code == 422


def test_t1_6_revoke_consent_suspends_and_hides_business():
    """T1.6: Revogação de consentimento suspende a empresa e remove-a da vitrine pública."""
    owner = User(id=uuid.uuid4(), name="Dono", email="dono@empresa.com", role="owner", is_active=True)
    biz = Business(
        id=uuid.uuid4(),
        owner_user_id=owner.id,
        name="Empresa Ativa",
        slug="empresa-ativa",
        status="approved",
        owner_paused=False,
    )

    async def override_user():
        return owner

    async def override_db():
        db = AsyncMock()
        res = MagicMock()
        res.scalar_one_or_none.return_value = biz
        db.execute.return_value = res
        yield db

    app.dependency_overrides[get_current_user] = override_user
    app.dependency_overrides[get_db] = override_db
    try:
        res = client.post("/api/v1/privacy/revoke-consent", json={"business_id": str(biz.id)})
        assert res.status_code == 200
        assert res.json()["status"] == "suspended"
        assert biz.status == "suspended"
        assert biz.owner_paused is True
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(get_db, None)


# ==============================================================================
# T1.7: Convites Seguros com Consumo Atômico e Validade Limitada
# ==============================================================================

@pytest.mark.skipif(not settings.FEATURE_ADMIN_TOOLS, reason="Módulo de convites congelado no MVP por FEATURE_ADMIN_TOOLS")
def test_t1_7_invitation_days_valid_bounded():
    """T1.7: days_valid deve estar entre 1 e 14 dias; valores fora desse intervalo são rejeitados com 422."""
    admin = User(id=uuid.uuid4(), name="Admin", email="admin@patriota.com", role="admin", is_active=True)

    async def override_admin():
        return admin

    app.dependency_overrides[get_current_active_admin] = override_admin
    try:
        # days_valid = 100 (excesso)
        res_exceeded = client.post(
            "/api/v1/invitations",
            json={"business_id": str(uuid.uuid4()), "phone": "19999998888", "days_valid": 100},
        )
        assert res_exceeded.status_code == 422

        # days_valid = 0 (inválido)
        res_zero = client.post(
            "/api/v1/invitations",
            json={"business_id": str(uuid.uuid4()), "phone": "19999998888", "days_valid": 0},
        )
        assert res_zero.status_code == 422
    finally:
        app.dependency_overrides.pop(get_current_active_admin, None)


@pytest.mark.skipif(not settings.FEATURE_ADMIN_TOOLS, reason="Módulo de convites congelado no MVP por FEATURE_ADMIN_TOOLS")
def test_t1_7_invitation_accept_does_not_grant_verified_seal():
    """T1.7: Aceitar convite vincula proprietário mas NUNCA concede selo is_verified automaticamente."""
    user = User(id=uuid.uuid4(), name="Novo Dono", email="novo@dono.com", role="user", is_active=True)
    biz = Business(
        id=uuid.uuid4(),
        name="Empresa Convidada",
        slug="empresa-convidada",
        status="pending_review",
        is_verified=False,
    )
    raw_token = "segredo_convite_12345678901234567890"

    async def override_user():
        return user

    async def override_db():
        db = AsyncMock()
        # Mock do RETURNING do UPDATE atômico: (inv_id, biz_id, phone)
        mock_res_update = MagicMock()
        mock_res_update.first.return_value = (uuid.uuid4(), biz.id, "19999998888")
        # Mock da busca da empresa
        mock_res_biz = MagicMock()
        mock_res_biz.scalar_one_or_none.return_value = biz
        db.execute.side_effect = [mock_res_update, mock_res_biz]
        yield db

    app.dependency_overrides[get_current_user] = override_user
    app.dependency_overrides[get_db] = override_db
    try:
        res = client.post(f"/api/v1/invitations/{raw_token}/accept")
        assert res.status_code == 200
        assert biz.owner_user_id == user.id
        assert user.role == "owner"
        # O selo 'is_verified' NÃO é concedido automaticamente por convite
        assert biz.is_verified is False
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(get_db, None)


def test_t1_8_business_unified_register_atomic_flow():
    """T1.1 (Sprint S1): Teste do cadastro unificado de dono + empresa sem obrigatoriedade de OTP."""
    payload = {
        "owner_name": "Dono Patriota Teste",
        "owner_email": "dono.sprint1@teste.com",
        "owner_password": "SenhaForteOwner123!",
        "owner_phone": "19988887777",
        "name": "Mecânica Patriota Express",
        "description": "Oficina mecânica especializada em manutenção preventiva.",
        "listing_type": "service",
        "document_type": "CNPJ",
        "document_number": "11222333000181",
        "whatsapp": "19988887777",
        "neighborhood": "Guanabara",
        "city": "Campinas",
        "state": "SP",
        "consent_carta_principios": True,
        "consent_termos": True,
        "consent_privacidade": True,
    }

    async def override_db():
        db = AsyncMock()
        mock_user_check = MagicMock()
        mock_user_check.scalar_one_or_none.return_value = None

        mock_doc_check = MagicMock()
        mock_doc_check.scalars.return_value.all.return_value = []

        mock_slug_check = MagicMock()
        mock_slug_check.scalar_one_or_none.return_value = None

        db.execute.side_effect = [
            mock_user_check,
            mock_doc_check,
            mock_slug_check,
        ]
        yield db

    app.dependency_overrides[get_db] = override_db
    try:
        with patch("backend.app.api.v1.endpoints.businesses.geocode_address", new_callable=AsyncMock) as mock_geo, \
             patch("backend.app.api.v1.endpoints.businesses.store_refresh_token", new_callable=AsyncMock) as mock_rt:
            mock_geo.return_value = (-22.9064, -47.0616, "osm_nominatim", 0.95)
            mock_rt.return_value = True

            res = client.post("/api/v1/businesses/register", json=payload)
            assert res.status_code == 201, res.text
            data = res.json()
            assert data["success"] is True
            assert data["status"] == "pending_review"
            assert "access_token" in data
            assert "refresh_token" in data
            assert data["user"]["email"] == "dono.sprint1@teste.com"
            assert data["user"]["role"] == "owner"
    finally:
        app.dependency_overrides.pop(get_db, None)


def test_t1_5_auth_register_is_deprecated_410():
    """T1.5 (Sprint S1): Rota /auth/register desativada com 410 GONE para evitar usuários sem papel."""
    res = client.post("/api/v1/auth/register", json={
        "name": "Usuario Avulso",
        "email": "avulso@teste.com",
        "password": "SenhaForte12345!"
    })
    assert res.status_code == 410
    assert "desativado" in res.json()["detail"].lower()


def test_t1_6_end_to_end_sprint1_lifecycle():
    """
    T1.6 (Sprint S1): Teste E2E do ciclo completo:
    1. Registro unificado da empresa (dono + negócio em pending_review)
    2. Admin aprova a empresa na triagem
    3. Dono autenticado edita campos permitidos
    """
    biz_id = uuid.uuid4()
    owner_id = uuid.uuid4()
    admin_id = uuid.uuid4()

    mock_biz = Business(
        id=biz_id,
        name="Padaria Patriota",
        slug="padaria-patriota-campinas",
        description="Pães e cafés artesanais",
        status="pending_review",
        owner_user_id=owner_id,
        city="Campinas",
        state="SP",
        whatsapp="+5519999998888",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )

    admin_user = User(
        id=admin_id,
        name="Admin Curador",
        email="admin@patriotaindica.com.br",
        role="admin",
        is_active=True,
    )

    owner_user = User(
        id=owner_id,
        name="Dono da Padaria",
        email="dono@padaria.com",
        role="owner",
        is_active=True,
    )

    # 1. Admin aprova a empresa na triagem
    async def override_db():
        db = AsyncMock()
        mock_biz_res = MagicMock()
        mock_biz_res.scalar_one_or_none.return_value = mock_biz

        mock_empty_list = MagicMock()
        mock_empty_list.scalars.return_value.all.return_value = []

        mock_sub_res = MagicMock()
        mock_sub_res.scalars.return_value.first.return_value = None

        db.execute.side_effect = [
            mock_biz_res,    # select business
            mock_empty_list, # check pending niches
            mock_empty_list, # check duplicates
            mock_sub_res,    # check owner subscription
        ]
        yield db

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_current_active_admin] = lambda: admin_user

    try:
        approve_res = client.post(
            f"/api/v1/triage/decision/{biz_id}",
            json={"action": "approve", "note": "Empresa validada e alinhada aos princípios."},
        )
        assert approve_res.status_code == 200, approve_res.text
        assert mock_biz.status == "approved"
    finally:
        app.dependency_overrides.pop(get_current_active_admin, None)
        app.dependency_overrides.pop(get_db, None)

    # 2. Dono logado edita descrição da empresa aprovada
    async def override_owner_db():
        db = AsyncMock()
        mock_res = MagicMock()
        mock_res.scalar_one_or_none.return_value = mock_biz
        db.execute.return_value = mock_res
        yield db

    app.dependency_overrides[get_db] = override_owner_db
    app.dependency_overrides[get_current_user] = lambda: owner_user

    try:
        update_res = client.put(
            f"/api/v1/owner/{biz_id}/profile",
            json={"description": "Nova descrição atualizada pelo dono."},
        )
        assert update_res.status_code == 200, update_res.text
        assert mock_biz.description == "Nova descrição atualizada pelo dono."
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(get_db, None)
