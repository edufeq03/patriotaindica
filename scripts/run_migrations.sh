#!/usr/bin/env bash
# ==============================================================================
# Script para aplicar migrações SQL com controle de versão e idempotência (T6.1)
# ==============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

# 1. Se o ambiente virtual Python estiver presente, usar o runner avançado com validação de drift
if [ -f "${ROOT_DIR}/backend/venv/bin/python" ]; then
    echo "Executando runner Python com detecção de drift..."
    PYTHONPATH="${ROOT_DIR}" "${ROOT_DIR}/backend/venv/bin/python" "${ROOT_DIR}/database/scripts/migrate.py" "$@"
    exit 0
fi

# 2. Caso contrário, executar via Docker / psql com tabela de controle schema_migrations
DB_CONTAINER="${1:-sites_patriotaindica-db-1}"
DB_USER="${POSTGRES_USER:-postgres}"
DB_NAME="${POSTGRES_DB:-patriotaindica}"
MIGRATIONS_DIR="${ROOT_DIR}/database/migrations"

echo "=========================================================="
echo "Aplicando migrações em ${DB_NAME} (Container: ${DB_CONTAINER})"
echo "=========================================================="

# Criar tabela de controle se não existir
docker exec -i "${DB_CONTAINER}" psql -U "${DB_USER}" -d "${DB_NAME}" -c \
  "CREATE TABLE IF NOT EXISTS schema_migrations (version VARCHAR(150) PRIMARY KEY, applied_at TIMESTAMPTZ DEFAULT NOW(), checksum VARCHAR(64) NOT NULL);" > /dev/null

for sql_file in $(ls "${MIGRATIONS_DIR}"/*.sql | sort); do
    filename=$(basename "${sql_file}")
    
    # Checar se já foi aplicada
    applied=$(docker exec -i "${DB_CONTAINER}" psql -U "${DB_USER}" -d "${DB_NAME}" -t -c \
      "SELECT count(*) FROM schema_migrations WHERE version = '${filename}';" | tr -d '[:space:]')

    if [ "${applied}" = "1" ]; then
        echo "✓ ${filename} (já aplicada)"
    else
        echo "-> Executando migração: ${filename}..."
        checksum=$(sha256sum "${sql_file}" | awk '{print $1}')
        docker exec -i "${DB_CONTAINER}" psql -U "${DB_USER}" -d "${DB_NAME}" < "${sql_file}" > /dev/null
        docker exec -i "${DB_CONTAINER}" psql -U "${DB_USER}" -d "${DB_NAME}" -c \
          "INSERT INTO schema_migrations (version, checksum) VALUES ('${filename}', '${checksum}');" > /dev/null
        echo "✓ ${filename} aplicada com sucesso."
    fi
done

echo "=========================================================="
echo " Todas as migrações foram verificadas e aplicadas com sucesso!"
echo "=========================================================="
