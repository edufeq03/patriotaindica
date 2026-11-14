#!/usr/bin/env sh
set -e

echo "==> Verificando e aplicando migrações de banco de dados..."

MIGRATE_SCRIPT=""
if [ -f "/app/database/scripts/migrate.py" ]; then
    MIGRATE_SCRIPT="/app/database/scripts/migrate.py"
elif [ -f "/app/backend/database/scripts/migrate.py" ]; then
    MIGRATE_SCRIPT="/app/backend/database/scripts/migrate.py"
elif [ -f "database/scripts/migrate.py" ]; then
    MIGRATE_SCRIPT="database/scripts/migrate.py"
elif [ -f "backend/database/scripts/migrate.py" ]; then
    MIGRATE_SCRIPT="backend/database/scripts/migrate.py"
fi

if [ -n "$MIGRATE_SCRIPT" ]; then
    echo "Executando: python $MIGRATE_SCRIPT"
    python "$MIGRATE_SCRIPT" || {
        echo "AVISO: Falha ao rodar migrate.py automaticamente no startup. Prosseguindo com startup do servidor..."
    }
else
    echo "AVISO: Script migrate.py não encontrado nos caminhos padrão."
fi

echo "==> Iniciando Uvicorn..."
exec uvicorn backend.app.main:app --host 0.0.0.0 --port 8000

