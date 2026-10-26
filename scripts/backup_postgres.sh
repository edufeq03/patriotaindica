#!/usr/bin/env bash
# ==============================================================================
# Patriota Indica - Backup Diário Criptografado do PostgreSQL (M14)
# Execução recomendada via Cron: 0 3 * * * /app/scripts/backup_postgres.sh
# ==============================================================================
set -euo pipefail

BACKUP_DIR="${BACKUP_DIR:-/var/backups/patriotaindica}"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
DB_CONTAINER="${DB_CONTAINER:-patriotaindica-db-1}"
DB_NAME="${DB_NAME:-patriotaindica}"
DB_USER="${DB_USER:-postgres}"
ENCRYPTION_KEY="${BACKUP_ENCRYPTION_KEY:-}" # Defina no .env do servidor

mkdir -p "${BACKUP_DIR}"

RAW_BACKUP="${BACKUP_DIR}/dump_${DB_NAME}_${TIMESTAMP}.sql.gz"
ENC_BACKUP="${RAW_BACKUP}.enc"

echo "[$(date -Iseconds)] Iniciando backup do banco ${DB_NAME}..."

# 1. Gerar dump comprimido direto do container Postgres
docker exec -t "${DB_CONTAINER}" pg_dump -U "${DB_USER}" -d "${DB_NAME}" -F c -b -v > "${RAW_BACKUP}"

# 2. Criptografar com AES-256-CBC se chave fornecida
if [ -n "${ENCRYPTION_KEY}" ]; then
    echo "[$(date -Iseconds)] Criptografando backup com AES-256..."
    openssl enc -aes-256-cbc -salt -pbkdf2 -in "${RAW_BACKUP}" -out "${ENC_BACKUP}" -pass pass:"${ENCRYPTION_KEY}"
    rm -f "${RAW_BACKUP}"
    FINAL_FILE="${ENC_BACKUP}"
else
    echo "[$(date -Iseconds)] AVISO: BACKUP_ENCRYPTION_KEY nao definida. Backup mantido em gzip sem criptografia extra."
    FINAL_FILE="${RAW_BACKUP}"
fi

# 3. Gerar SHA-256 checksum para integridade
sha256sum "${FINAL_FILE}" > "${FINAL_FILE}.sha256"

echo "[$(date -Iseconds)] Backup concluido com sucesso: ${FINAL_FILE}"
echo "[$(date -Iseconds)] Tamanho: $(du -h "${FINAL_FILE}" | cut -f1)"

# 4. Rotatividade: manter ultimos 30 dias de backups
echo "[$(date -Iseconds)] Removendo backups locais com mais de 30 dias..."
find "${BACKUP_DIR}" -name "dump_${DB_NAME}_*" -mtime +30 -delete

# 5. Recomendacao para envio a storage externo (ex: Rclone / AWS S3 / Wasabi):
# rclone copy "${FINAL_FILE}" remote-backup:patriotaindica-backups/
