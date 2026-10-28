#!/usr/bin/env bash
# ==============================================================================
# Patriota Indica - Backup Seguro e Criptografado do PostgreSQL (M14)
# Suporta: Docker Container (Docker Compose/Easypanel) ou pg_dump direto via DATABASE_SYNC_URL
# Execução recomendada via Cron: 0 3 * * * /caminho/scripts/backup_postgres.sh
# ==============================================================================
set -euo pipefail

BACKUP_DIR="${BACKUP_DIR:-/var/backups/patriotaindica}"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
DB_NAME="${POSTGRES_DB:-patriotaindica}"
DB_USER="${POSTGRES_USER:-postgres}"
DB_CONTAINER="${DB_CONTAINER:-}"
DATABASE_SYNC_URL="${DATABASE_SYNC_URL:-}"
ENCRYPTION_KEY="${BACKUP_ENCRYPTION_KEY:-}" # Defina no .env do servidor

mkdir -p "${BACKUP_DIR}"

RAW_BACKUP="${BACKUP_DIR}/dump_${DB_NAME}_${TIMESTAMP}.sql.gz"
ENC_BACKUP="${RAW_BACKUP}.enc"

echo "[$(date -Iseconds)] Iniciando rotina de backup do banco '${DB_NAME}'..."

# 1. Gerar dump comprimido
if command -v pg_dump >/dev/null 2>&1 && [ -n "${DATABASE_SYNC_URL}" ]; then
    echo "[$(date -Iseconds)] Gerando dump via pg_dump direto usando DATABASE_SYNC_URL..."
    pg_dump "${DATABASE_SYNC_URL}" -F c -b -v > "${RAW_BACKUP}"
elif command -v docker >/dev/null 2>&1; then
    # Auto-detectar container se DB_CONTAINER não foi fixado
    if [ -z "${DB_CONTAINER}" ]; then
        DB_CONTAINER=$(docker ps --filter "name=db" --format "{{.Names}}" | grep -E "patriotaindica|db" | head -n 1 || true)
        if [ -z "${DB_CONTAINER}" ]; then
            DB_CONTAINER="patriotaindica-db-1"
        fi
    fi
    echo "[$(date -Iseconds)] Gerando dump via container Docker '${DB_CONTAINER}'..."
    docker exec -t "${DB_CONTAINER}" pg_dump -U "${DB_USER}" -d "${DB_NAME}" -F c -b -v > "${RAW_BACKUP}"
else
    echo "ERRO: Nem pg_dump nem Docker foram encontrados no ambiente para gerar o backup."
    exit 1
fi

# 2. Criptografar com AES-256-CBC se chave fornecida
if [ -n "${ENCRYPTION_KEY}" ]; then
    echo "[$(date -Iseconds)] Criptografando backup com AES-256-CBC (PBKDF2)..."
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

# 4. Rotatividade: manter ultimos 30 dias de backups locais
echo "[$(date -Iseconds)] Removendo backups locais com mais de 30 dias..."
find "${BACKUP_DIR}" -name "dump_${DB_NAME}_*" -mtime +30 -delete

# 5. Sincronizacao remota opcional (Rclone / AWS S3 / Wasabi / B2)
if command -v rclone >/dev/null 2>&1 && [ -n "${RCLONE_REMOTE_DEST:-}" ]; then
    echo "[$(date -Iseconds)] Enviando backup para storage remoto via Rclone: ${RCLONE_REMOTE_DEST}..."
    rclone copy "${FINAL_FILE}" "${RCLONE_REMOTE_DEST}"
    rclone copy "${FINAL_FILE}.sha256" "${RCLONE_REMOTE_DEST}"
    echo "[$(date -Iseconds)] Envio remoto finalizado com sucesso."
fi

echo "[$(date -Iseconds)] Rotina de backup finalizada."
