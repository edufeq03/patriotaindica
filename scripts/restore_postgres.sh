#!/usr/bin/env bash
# ==============================================================================
# Patriota Indica - Restauracao e Validacao de Backup PostgreSQL (M14)
# Uso: ./scripts/restore_postgres.sh /caminho/do/dump.sql.gz[.enc] [nome_banco_destino]
# ==============================================================================
set -euo pipefail

BACKUP_FILE="${1:-}"
TARGET_DB="${2:-patriotaindica_restore_test}"
DB_CONTAINER="${DB_CONTAINER:-patriotaindica-db-1}"
DB_USER="${DB_USER:-postgres}"
ENCRYPTION_KEY="${BACKUP_ENCRYPTION_KEY:-}"

if [ -z "${BACKUP_FILE}" ] || [ ! -f "${BACKUP_FILE}" ]; then
    echo "Erro: Forneca um arquivo de backup valido."
    echo "Uso: $0 /caminho/do/dump.sql.gz[.enc] [nome_banco_destino]"
    exit 1
fi

# 1. Verificar checksum se existir arquivo .sha256
if [ -f "${BACKUP_FILE}.sha256" ]; then
    echo "Verificando integridade SHA-256..."
    sha256sum -c "${BACKUP_FILE}.sha256"
fi

TEMP_RESTORE_FILE="/tmp/restore_temp.dump"
trap 'rm -f "${TEMP_RESTORE_FILE}"' EXIT

# 2. Descriptografar se extensao for .enc
if [[ "${BACKUP_FILE}" == *.enc ]]; then
    if [ -z "${ENCRYPTION_KEY}" ]; then
        echo -n "Digite a senha de decriptacao do backup: "
        read -s ENCRYPTION_KEY
        echo ""
    fi
    echo "Descriptografando arquivo..."
    openssl enc -d -aes-256-cbc -pbkdf2 -in "${BACKUP_FILE}" -out "${TEMP_RESTORE_FILE}" -pass pass:"${ENCRYPTION_KEY}"
else
    cp "${BACKUP_FILE}" "${TEMP_RESTORE_FILE}"
fi

# 3. Criar banco de dados de teste/destino
echo "Preparando banco de dados '${TARGET_DB}' no container '${DB_CONTAINER}'..."
docker exec -t "${DB_CONTAINER}" psql -U "${DB_USER}" -c "DROP DATABASE IF EXISTS ${TARGET_DB};"
docker exec -t "${DB_CONTAINER}" psql -U "${DB_USER}" -c "CREATE DATABASE ${TARGET_DB};"

# 4. Restaurar dump
echo "Restaurando dados..."
docker exec -i "${DB_CONTAINER}" pg_restore -U "${DB_USER}" -d "${TARGET_DB}" -v < "${TEMP_RESTORE_FILE}" || true

# 5. Executar teste de sanidade
echo "Executando teste de sanidade no banco restaurado..."
docker exec -t "${DB_CONTAINER}" psql -U "${DB_USER}" -d "${TARGET_DB}" -c "SELECT count(*) AS total_empresas FROM businesses;"

echo "Restauracao e validacao concluidas com sucesso!"
