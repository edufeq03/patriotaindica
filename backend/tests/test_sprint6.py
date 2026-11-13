import hashlib
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from backend.app.main import app
from database.scripts.migrate import get_file_checksum, run_migrations

client = TestClient(app)


def test_t6_1_migration_checksum_and_drift_detection(tmp_path: Path):
    """T6.1: Valida o cálculo de hash SHA-256 e a detecção de integridade das migrações."""
    test_file = tmp_path / "999_test_migration.sql"
    test_file.write_text("CREATE TABLE test_drift (id INT);", encoding="utf-8")

    checksum_1 = get_file_checksum(test_file)
    expected_hash = hashlib.sha256(b"CREATE TABLE test_drift (id INT);").hexdigest()
    assert checksum_1 == expected_hash

    # Se o arquivo for alterado, o hash deve mudar (detectando drift)
    test_file.write_text("CREATE TABLE test_drift (id INT, modified BOOLEAN);", encoding="utf-8")
    checksum_2 = get_file_checksum(test_file)
    assert checksum_1 != checksum_2


@pytest.mark.anyio
async def test_t6_1_runner_detects_drift_in_applied_migrations():
    """T6.1: Runner reporta erro caso um arquivo aplicado tenha sido alterado no disco."""
    mock_db_url = "postgresql+asyncpg://user:pass@localhost:5432/fake_db"

    mock_conn = AsyncMock()
    mock_conn.fetch.return_value = [{"version": "001_initial_schema.sql", "checksum": "tampered_hash_12345"}]
    mock_conn.execute.return_value = None

    with patch("database.scripts.migrate.asyncpg.connect", AsyncMock(return_value=mock_conn)):
        exit_code = await run_migrations(database_url=mock_db_url, check_drift_only=True, verbose=False)
        assert exit_code == 1


def test_t6_2_safe_dtos_do_not_leak_internal_orm_fields():
    """T6.2: Garante que o retorno das buscas expõe apenas DTOs públicos sem vazar vetores ou segredos internos."""
    res = client.get("/api/v1/search")
    assert res.status_code == 200
    data = res.json()
    assert "results" in data
    for item in data.get("results", []):
        # Campos internos proibidos no DTO público
        assert "search_vector" not in item
        assert "password_hash" not in item
        assert "document_number" not in item  # LGPD: CPF/CNPJ não exposto na busca pública


def test_t6_3_security_audit_dead_endpoints_return_404():
    """T6.3: Rotas de risco e endpoints de teste/bootstrap removidos devem retornar estritamente 404."""
    dead_routes = [
        "/api/v1/system/migrate",
        "/api/v1/reset-businesses",
        "/api/v1/test-evolution",
        "/api/v1/payments/simulate-activation",
        "/api/v1/audit",
    ]
    for route in dead_routes:
        res_get = client.get(route)
        res_post = client.post(route)
        assert res_get.status_code == 404, f"Rota {route} deveria retornar 404 no GET"
        assert res_post.status_code == 404, f"Rota {route} deveria retornar 404 no POST"
