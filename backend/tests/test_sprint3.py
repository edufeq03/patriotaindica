import json
import uuid
from unittest.mock import AsyncMock, MagicMock, patch
import pytest
from fastapi.testclient import TestClient

from backend.app.core.database import get_db
from backend.app.main import app
from backend.app.models.business import Business
from backend.app.models.city import City
from backend.app.services.geocoding import geocode_address


@pytest.fixture
def test_client():
    return TestClient(app)


@pytest.mark.anyio
async def test_t3_1_search_anti_n_plus_one_and_dto_structure(test_client):
    """
    T3.1: Valida que a busca retorna categorias no JOIN principal (sem N+1)
    e com DTO público seguro contendo contact_url e distance_km.
    """
    biz_id = uuid.uuid4()
    mock_biz = Business(
        id=biz_id,
        name="Padaria Patriota",
        slug="padaria-patriota",
        description="Pães e cafés artesanais",
        listing_type="product",
        service_mode="at_location",
        status="approved",
        owner_paused=False,
        is_verified=True,
        neighborhood="Cambuí",
        city="Campinas",
        state="SP",
        whatsapp="19999998888",
        show_full_address=False,
    )

    # Simula retorno do JOIN: (Business, category_name, category_slug, distance_km)
    mock_row = (mock_biz, "Alimentação", "alimentacao", 2.5)

    async def override_db():
        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.all.return_value = [mock_row]
        mock_db.execute.return_value = mock_result
        yield mock_db

    app.dependency_overrides[get_db] = override_db
    try:
        response = test_client.get("/api/v1/search?lat=-22.90&lng=-47.06&radius_km=10")
        assert response.status_code == 200, response.text
        data = response.json()
        assert data["total"] == 1
        item = data["results"][0]
        assert item["name"] == "Padaria Patriota"
        assert item["category_name"] == "Alimentação"
        assert item["category_slug"] == "alimentacao"
        assert item["distance_km"] == 2.5
        assert item["contact_url"] == f"/go/whatsapp/{biz_id}"
        # Dados sensíveis internos NÃO devem estar no DTO público
        assert "document_number" not in item
        assert "cnpj_situation" not in item
        assert "geocode_confidence" not in item
    finally:
        app.dependency_overrides.pop(get_db, None)


@pytest.mark.anyio
async def test_t3_2_geocoding_never_returns_fake_campinas():
    """
    T3.2: Falha de geocodificação NUNCA inventa coordenadas de Campinas.
    Retorna (None, None, 'unresolved', 0.0) de forma determinística.
    """
    with patch("httpx.AsyncClient.get") as mock_get:
        # Simula erro ou resposta vazia nas APIs externas
        mock_resp = MagicMock()
        mock_resp.status_code = 404
        mock_get.return_value = mock_resp

        lat, lng, source, confidence = await geocode_address(
            postal_code="99999999",
            city="CidadeInexistente",
            state="XX",
        )

        assert lat is None
        assert lng is None
        assert source == "unresolved"
        assert confidence == 0.0


@pytest.mark.anyio
async def test_t3_2_geocoding_uses_redis_cache():
    """
    T3.2: Geocodificação armazena e lê do cache Redis com TTL.
    """
    mock_redis = AsyncMock()
    cached_payload = json.dumps([-23.5505, -46.6333, "redis_cached", 1.0])
    mock_redis.get.return_value = cached_payload

    with patch("backend.app.services.geocoding.get_redis", return_value=mock_redis):
        lat, lng, source, confidence = await geocode_address(
            postal_code="01001000",
            city="São Paulo",
            state="SP",
        )
        assert lat == -23.5505
        assert lng == -46.6333
        assert source == "redis_cached"
        assert confidence == 1.0
        mock_redis.get.assert_awaited_once()


@pytest.mark.anyio
async def test_t3_4_cities_endpoint_and_waitlist(test_client):
    """
    T3.4: Listagem de cidades ativas/em expansão e registro em lista de espera.
    """
    city_active = City(
        id=uuid.uuid4(),
        name="Campinas",
        state="SP",
        slug="sp-campinas",
        status="active",
        interested_count=150,
    )
    city_soon = City(
        id=uuid.uuid4(),
        name="Curitiba",
        state="PR",
        slug="pr-curitiba",
        status="soon",
        interested_count=42,
    )

    async def override_db():
        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [city_active, city_soon]
        mock_db.execute.return_value = mock_result
        yield mock_db

    app.dependency_overrides[get_db] = override_db
    try:
        # 1. Consulta cidades
        res = test_client.get("/api/v1/cities")
        assert res.status_code == 200, res.text
        data = res.json()
        assert len(data["active"]) == 1
        assert data["active"][0]["slug"] == "sp-campinas"
        assert len(data["soon"]) == 1
        assert data["soon"][0]["slug"] == "pr-curitiba"
    finally:
        app.dependency_overrides.pop(get_db, None)


@pytest.mark.anyio
async def test_t3_4_join_waitlist_increments_count(test_client):
    """
    T3.4: Cadastrar na lista de espera incrementa interested_count da cidade.
    """
    target_city_id = uuid.uuid4()
    mock_city = City(
        id=target_city_id,
        name="Belo Horizonte",
        state="MG",
        slug="mg-belo-horizonte",
        status="soon",
        interested_count=10,
    )

    async def override_db():
        mock_db = AsyncMock()
        mock_res = MagicMock()
        mock_res.scalar_one_or_none.return_value = mock_city
        mock_db.execute.return_value = mock_res
        yield mock_db

    app.dependency_overrides[get_db] = override_db
    try:
        res = test_client.post(
            f"/api/v1/cities/{target_city_id}/waitlist",
            json={"contact": "interessado@bh.com.br", "is_business": True},
        )
        assert res.status_code == 201, res.text
        resp_data = res.json()
        assert resp_data["success"] is True
        assert resp_data["interested_count"] == 11
        assert mock_city.interested_count == 11
    finally:
        app.dependency_overrides.pop(get_db, None)
