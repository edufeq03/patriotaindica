#!/usr/bin/env bash
# ==============================================================================
# Script para aplicar todas as migrações SQL no banco PostgreSQL do Docker
# ==============================================================================
set -euo pipefail

DB_CONTAINER="${1:-sites_patriotaindica-db-1}"
DB_USER="${POSTGRES_USER:-postgres}"
DB_NAME="${POSTGRES_DB:-patriotaindica}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MIGRATIONS_DIR="${SCRIPT_DIR}/../database/migrations"

echo "=========================================================="
echo "Aplicando migrações em ${DB_NAME} (Container: ${DB_CONTAINER})"
echo "=========================================================="

for sql_file in $(ls "${MIGRATIONS_DIR}"/*.sql | sort); do
    filename=$(basename "${sql_file}")
    echo "-> Executando migração: ${filename}..."
    docker exec -i "${DB_CONTAINER}" psql -U "${DB_USER}" -d "${DB_NAME}" < "${sql_file}" > /dev/null
done

echo "=========================================================="
echo " Todas as migrações foram aplicadas com sucesso!"
echo "=========================================================="
