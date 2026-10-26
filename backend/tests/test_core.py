import pytest
from datetime import timedelta
from backend.app.core.security import (
    create_access_token,
    decode_access_token,
    get_password_hash,
    verify_password,
)
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
    )
    assert app.name == "Padaria Artesanal"
    assert app.state == "SP"
    assert app.document_type == "CNPJ"
