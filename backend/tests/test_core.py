import pytest
from datetime import timedelta
from backend.app.core.security import (
    create_access_token,
    decode_access_token,
    get_password_hash,
    verify_password,
)
from pydantic import ValidationError
from backend.app.schemas.business import BusinessApplicationCreate
from backend.app.schemas.search import SearchQueryParams
from backend.app.api.v1.endpoints.businesses import slugify


def test_password_hashing():
    password = "minha_senha_segura_123"
    hashed = get_password_hash(password)
    assert hashed != password
    assert verify_password(password, hashed) is True
    assert verify_password("senha_errada", hashed) is False


def test_jwt_token_creation_and_decoding():
    user_id = "a0000000-0000-0000-0000-000000000001"
    role = "admin"
    token = create_access_token(subject=user_id, role=role, expires_delta=timedelta(minutes=15))
    assert isinstance(token, str)

    payload = decode_access_token(token)
    assert payload is not None
    assert payload["sub"] == user_id
    assert payload["role"] == role
    assert "exp" in payload


def test_slugify():
    raw_name = "Silva & Filhos - Instalações Elétricas (Campinas)"
    slug = slugify(raw_name)
    assert slug == "silva-filhos-instalacoes-eletricas-campinas"
    assert " " not in slug
    assert "ã" not in slug


def test_search_query_params_validation():
    # Parâmetros válidos
    params = SearchQueryParams(lat=-22.9056, lng=-47.0608, radius_km=25.0)
    assert params.lat == -22.9056
    assert params.radius_km == 25.0

    # Testar default radius
    params_default = SearchQueryParams(lat=-22.9056, lng=-47.0608)
    assert params_default.radius_km == 50.0
    assert params_default.page == 1
    assert params_default.limit == 20


def test_business_application_schema():
    app = BusinessApplicationCreate(
        name="Padaria Artesanal",
        whatsapp="19999998888",
        neighborhood="Cambuí",
        city="Campinas",
        state="SP",
        service_mode="at_location",
        document_number="12345678000195",
        consent_carta_principios=True,
        consent_termos=True,
        consent_privacidade=True,
    )
    assert app.name == "Padaria Artesanal"
    assert app.state == "SP"
    assert app.document_type == "CNPJ"
    assert app.serves_at_location is True
    assert app.consent_carta_principios is True

    # T1.6: Cadastro sem checkbox de consentimento é rejeitado pela validação (422)
    with pytest.raises(ValidationError):
        BusinessApplicationCreate(
            name="Padaria Sem Consentimento",
            whatsapp="19999998888",
            neighborhood="Cambuí",
            city="Campinas",
            state="SP",
            consent_termos=True,
            consent_privacidade=True,
        )


def test_business_application_multi_attendance_modes():
    # 1. Caso com as 3 opções marcadas juntas
    app_all_three = BusinessApplicationCreate(
        name="Empresa Multi-Canal",
        whatsapp="19999998888",
        neighborhood="Cambuí",
        city="Campinas",
        state="SP",
        serves_at_location=True,
        serves_at_customer=True,
        serves_online=True,
        service_radius_km=30,
        document_number="12345678000195",
        consent_carta_principios=True,
        consent_termos=True,
        consent_privacidade=True,
    )
    assert app_all_three.serves_at_location is True
    assert app_all_three.serves_at_customer is True
    assert app_all_three.serves_online is True
    assert app_all_three.service_mode == "both"

    # 2. Caso apenas online
    app_online_only = BusinessApplicationCreate(
        name="Consultoria 100% Online",
        whatsapp="19999998888",
        neighborhood="Centro",
        city="Campinas",
        state="SP",
        serves_at_location=False,
        serves_at_customer=False,
        serves_online=True,
        document_number="12345678000195",
        consent_carta_principios=True,
        consent_termos=True,
        consent_privacidade=True,
    )
    assert app_online_only.serves_online is True
    assert app_online_only.service_mode == "online"

    # 3. Caso nenhum método selecionado -> deve falhar na validação
    with pytest.raises(ValueError, match="Selecione ao menos um método de atendimento"):
        BusinessApplicationCreate(
            name="Empresa Sem Metodo",
            whatsapp="19999998888",
            neighborhood="Centro",
            city="Campinas",
            state="SP",
            serves_at_location=False,
            serves_at_customer=False,
            serves_online=False,
            document_number="12345678000195",
            consent_carta_principios=True,
            consent_termos=True,
            consent_privacidade=True,
        )


@pytest.mark.anyio
async def test_admin_rbac_enforcement():
    from backend.app.core.security import get_current_active_admin
    from backend.app.models.user import User
    from fastapi import HTTPException

    # Usuário comum não pode acessar recursos de admin
    regular_user = User(name="Comum", email="comum@teste.com", role="user", is_active=True)
    with pytest.raises(HTTPException) as exc_info:
        await get_current_active_admin(current_user=regular_user)
    assert exc_info.value.status_code == 403

    # Administrador deve passar normalmente
    admin_user = User(name="Admin", email="admin@teste.com", role="admin", is_active=True)
    result = await get_current_active_admin(current_user=admin_user)
    assert result.role == "admin"


def test_invalid_jwt_decoding():
    assert decode_access_token("invalid.token.structure") is None
    assert decode_access_token("") is None


def test_decode_token_requires_iss_and_aud():
    import jwt
    from backend.app.core.config import settings

    # Token sem aud ou iss deve ser rejeitado (sem fallback tolerante)
    token_without_aud = jwt.encode({"sub": "user123"}, settings.JWT_SECRET_KEY, algorithm="HS256")
    assert decode_access_token(token_without_aud) is None

    # Token com segredo incorreto/antigo deve falhar
    token_wrong_secret = jwt.encode(
        {"sub": "user123", "aud": settings.JWT_AUDIENCE, "iss": settings.JWT_ISSUER},
        "wrong_secret_123456789012345678901234567890123456789012345678901234567890",
        algorithm="HS256",
    )
    assert decode_access_token(token_wrong_secret) is None


def test_weak_jwt_secret_rejected():
    from backend.app.core.config import Settings
    with pytest.raises(ValueError, match="mínimo 64 caracteres"):
        Settings(JWT_SECRET_KEY="short_key_123")
    
    # Validador deve rejeitar todos os termos da blocklist
    for term in ["sua_chave", "dev_key", "change", "secret", "example", "exemplo"]:
        with pytest.raises(ValueError, match="termo proibido"):
            Settings(JWT_SECRET_KEY=f"0123456789abcdef0123456789abcdef_{term}_0123456789abcdef0123456789abcdef")


@pytest.mark.anyio
async def test_otp_security_service():
    from backend.app.services.otp import OTPService, WhatsAppProvider

    class MockProvider(WhatsAppProvider):
        def __init__(self):
            self.last_code = None

        async def send_otp(self, phone: str, code: str, business_name: str):
            self.last_code = code
            return True, None

    mock_provider = MockProvider()
    service = OTPService(provider=mock_provider)
    biz_id = "test-business-uuid-123"

    # 1. Solicitar OTP
    ok, msg = await service.request_otp(biz_id, "19999998888", "Empresa Teste")
    assert ok is True
    assert mock_provider.last_code is not None

    # O código bruto não pode estar gravado em texto claro no cache
    record = service._cache.get(f"claim:{biz_id}")
    assert record is not None
    assert mock_provider.last_code != record["hash"]

    # 2. Tentativa incorreta
    valid, err_msg = service.verify_otp(biz_id, "000000")
    assert valid is False
    assert "tentativa" in err_msg.lower()

    # 3. Código 123456 NUNCA deve ser aceito como backdoor
    valid_backdoor, _ = service.verify_otp(biz_id, "123456")
    assert valid_backdoor is False

    # 4. Código correto
    valid, success_msg = service.verify_otp(biz_id, mock_provider.last_code)
    assert valid is True

    # 5. Código consumido (uso único)
    valid_again, _ = service.verify_otp(biz_id, mock_provider.last_code)
    assert valid_again is False


@pytest.mark.anyio
async def test_rate_limit_enforcement():
    from backend.app.core.rate_limit import check_rate_limit
    from fastapi import HTTPException

    test_key = "test:ratelimit:unique_key_123"
    # Limite de 2 requisições por segundo
    await check_rate_limit(test_key, limit=2, window_seconds=10)
    await check_rate_limit(test_key, limit=2, window_seconds=10)

    # A terceira deve falhar com 429
    with pytest.raises(HTTPException) as exc_info:
        await check_rate_limit(test_key, limit=2, window_seconds=10)
    assert exc_info.value.status_code == 429


def test_validate_external_url_security():
    from backend.app.api.v1.endpoints.redirects import validate_external_url
    from fastapi import HTTPException

    # URLs seguras
    assert validate_external_url("https://minhaempresa.com.br") == "https://minhaempresa.com.br"
    assert validate_external_url("blog.patriota.com") == "https://blog.patriota.com"

    # SSRF / Localhost / IPs privados bloqueados (H5)
    with pytest.raises(HTTPException):
        validate_external_url("http://localhost/admin")
    with pytest.raises(HTTPException):
        validate_external_url("http://127.0.0.1:8000")
    with pytest.raises(HTTPException):
        validate_external_url("http://192.168.1.100")
    with pytest.raises(HTTPException):
        validate_external_url("http://10.0.0.1")
    with pytest.raises(HTTPException):
        validate_external_url("http://user:secretpassword@empresa.com.br")
    with pytest.raises(HTTPException):
        validate_external_url("ftp://empresa.com.br")


def test_brazilian_validators():
    from backend.app.core.validators import validate_cpf, validate_cnpj, BRAZIL_STATES

    # UFs
    assert "SP" in BRAZIL_STATES
    assert "PR" in BRAZIL_STATES
    assert "XX" not in BRAZIL_STATES

    # CPF
    assert validate_cpf("11111111111") is False  # Sequência idêntica
    assert validate_cpf("12345678900") is False  # Dígito falso
    assert validate_cpf("52998224725") is True   # CPF matematicamente válido

    # CNPJ
    assert validate_cnpj("00000000000000") is False
    assert validate_cnpj("11222333000181") is True   # CNPJ matematicamente válido
    assert validate_cnpj("11222333000199") is False  # Dígito falso


def test_business_application_validation_hardening():
    from backend.app.schemas.business import BusinessApplicationCreate, ReportCreate
    from pydantic import ValidationError

    # UF inválida
    with pytest.raises(ValidationError):
        BusinessApplicationCreate(
            name="Loja Teste",
            whatsapp="11999998888",
            neighborhood="Centro",
            city="Curitiba",
            state="INVALID",
        )

    # Honeypot preenchido (Anti-bot H2)
    with pytest.raises(ValidationError):
        BusinessApplicationCreate(
            name="Loja Teste",
            whatsapp="11999998888",
            neighborhood="Centro",
            city="Curitiba",
            state="PR",
            website_url_hp="http://spam-bot-link.com",
        )

    # Report com honeypot
    with pytest.raises(ValidationError):
        ReportCreate(
            reason="Fraude",
            website_url_hp="http://spam.com",
        )


@pytest.mark.anyio
async def test_server_geocoding_does_not_fake_campinas():
    from backend.app.services.geocoding import geocode_address

    # Endereço inexistente não deve nunca fingir que é centro de Campinas
    lat, lng, source, conf = await geocode_address(
        postal_code="00000000",
        city="Cidade Inexistente",
        state="XX",
    )
    # Não deve ter retornado o centro fixo de Campinas (-22.9056, -47.0608)
    assert lat != -22.9056
    assert lng != -47.0608
    assert source == "unresolved"
    assert conf == 0.0


def test_niche_validator_rules():
    from backend.app.core.niche_validator import validate_and_normalize_niche_name

    # Válidos (Sec. 4.2)
    assert validate_and_normalize_niche_name("Cuidador de Iguanas Selvagens") == "Cuidador de Iguanas Selvagens"
    assert validate_and_normalize_niche_name("Energia Solar Off-Grid & Baterias") == "Energia Solar Off-Grid & Baterias"
    assert validate_and_normalize_niche_name("Pães & Doces Artesanais") == "Pães & Doces Artesanais"

    # Inválidos (Sec. 4.2)
    with pytest.raises(ValueError):
        validate_and_normalize_niche_name("Ab")  # < 3 caracteres
    with pytest.raises(ValueError):
        validate_and_normalize_niche_name("A" * 65)  # > 60 caracteres
    with pytest.raises(ValueError):
        validate_and_normalize_niche_name("Eletricistaaaaa")  # repetição abusiva
    with pytest.raises(ValueError):
        validate_and_normalize_niche_name("123456")  # só números
    with pytest.raises(ValueError):
        validate_and_normalize_niche_name("Cuidador de Iguana http://golpe.com")  # URL
    with pytest.raises(ValueError):
        validate_and_normalize_niche_name("Ligue 19999998888")  # telefone
    with pytest.raises(ValueError):
        # Homógrafo cirílico (letra 'а' cirílica imitada)
        validate_and_normalize_niche_name("Advog\u0430do")


def test_triage_state_machine_rules():
    from backend.app.api.v1.endpoints.triage import VALID_TRANSITIONS

    # Transições legais
    assert "approved" in VALID_TRANSITIONS["pending_review"]
    assert "needs_info" in VALID_TRANSITIONS["pending_review"]
    assert "rejected" in VALID_TRANSITIONS["pending_review"]
    assert "suspended" in VALID_TRANSITIONS["approved"]
    assert "approved" in VALID_TRANSITIONS["suspended"]

    # Transições proibidas (M7)
    assert "approved" not in VALID_TRANSITIONS["rejected"]  # Não pode reaprovar direto
    assert "approved" not in VALID_TRANSITIONS["archived"]


def test_secure_image_upload_magic_bytes():
    from backend.app.services.media import validate_magic_bytes
    from fastapi import HTTPException

    # Assinaturas válidas (M10)
    fake_jpeg = b"\xff\xd8\xff\xe0" + b"\x00" * 20
    assert validate_magic_bytes(fake_jpeg) == "JPEG"

    fake_png = b"\x89PNG\r\n\x1a\n" + b"\x00" * 20
    assert validate_magic_bytes(fake_png) == "PNG"

    fake_webp = b"RIFF\x00\x00\x00\x00WEBP" + b"\x00" * 20
    assert validate_magic_bytes(fake_webp) == "WEBP"

    # SVG proibido (vetor XSS)
    fake_svg = b"<svg xmlns='http://www.w3.org/2000/svg'><script>alert(1)</script></svg>"
    with pytest.raises(HTTPException) as exc_info:
        validate_magic_bytes(fake_svg)
    assert exc_info.value.status_code == 400

    # Arquivo executável / desconhecido
    fake_exe = b"MZ\x90\x00\x03\x00\x00\x00\x04\x00\x00\x00\xff\xff"
    with pytest.raises(HTTPException):
        validate_magic_bytes(fake_exe)


def test_csv_formula_injection_sanitization():
    from backend.app.core.csv_sanitizer import sanitize_csv_cell

    # Células perigosas (M13)
    assert sanitize_csv_cell("=cmd|'/C calc'!A0") == "'=cmd|'/C calc'!A0"
    assert sanitize_csv_cell("+123456789") == "'+123456789"
    assert sanitize_csv_cell("-2+5") == "'-2+5"
    assert sanitize_csv_cell("@SUM(1,2)") == "'@SUM(1,2)"
    assert sanitize_csv_cell("\tscript") == "'\tscript"

    # Células normais
    assert sanitize_csv_cell("Padaria Pão Dourado") == "Padaria Pão Dourado"
    assert sanitize_csv_cell("19999998888") == "19999998888"


def test_invitation_hash_verification():
    from backend.app.api.v1.endpoints.invitations import hash_token

    raw_token = "secret_invite_token_xyz_123"
    hashed = hash_token(raw_token)

    # Nunca pode ser o token bruto
    assert hashed != raw_token
    # Deve ser hash SHA-256 de 64 caracteres hexadecimais
    assert len(hashed) == 64
    # Idempotente
    assert hash_token(raw_token) == hashed


def test_business_owner_update_security_hardening():
    from backend.app.api.v1.endpoints.owner import BusinessOwnerUpdate
    from pydantic import ValidationError

    # Atualizações válidas
    update = BusinessOwnerUpdate(
        description="Novo horário e descrição atualizada.",
        instagram="loja_oficial",
    )
    assert update.instagram == "loja_oficial"

    # Tentativa de bypass de status ou verificação pelo dono (H3)
    with pytest.raises(ValidationError):
        BusinessOwnerUpdate(
            description="Tentativa de auto-aprovação",
            status="approved",
        )

    with pytest.raises(ValidationError):
        BusinessOwnerUpdate(
            description="Tentativa de auto-selo",
            is_verified=True,
        )

    with pytest.raises(ValidationError):
        BusinessOwnerUpdate(
            description="Tentativa de troca de dono",
            owner_user_id="b0000000-0000-0000-0000-000000000001",
        )


def test_privacy_request_validation():
    from backend.app.api.v1.endpoints.privacy import PrivacyRequestCreate
    from pydantic import ValidationError

    # Válido (M11)
    req = PrivacyRequestCreate(
        request_type="deletion",
        email="titular@empresa.com.br",
        phone="19999998888",
        details="Solicito a exclusão definitiva do meu cadastro de MEI.",
    )
    assert req.request_type == "deletion"
    assert req.email == "titular@empresa.com.br"

    # Revogação de consentimento da Carta de Princípios
    req_rev = PrivacyRequestCreate(
        request_type="revocation",
        email="outro@exemplo.com",
    )
    assert req_rev.request_type == "revocation"

    # Tipo inválido rejeitado
    with pytest.raises(ValidationError):
        PrivacyRequestCreate(
            request_type="invalid_action",
            email="titular@empresa.com.br",
        )

    # E-mail inválido rejeitado
    with pytest.raises(ValidationError):
        PrivacyRequestCreate(
            request_type="deletion",
            email="not-an-email",
        )


def test_pyjwt_crypto_tokens():
    from backend.app.core.security import create_access_token, decode_access_token

    token = create_access_token(subject="user_123", role="owner")
    assert isinstance(token, str)

    payload = decode_access_token(token)
    assert payload is not None
    assert payload["sub"] == "user_123"
    assert payload["role"] == "owner"
    assert "exp" in payload
    assert "jti" in payload

    # Token adulterado deve retornar None
    tampered = token[:-4] + "abcd"
    assert decode_access_token(tampered) is None


