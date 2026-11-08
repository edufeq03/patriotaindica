#!/usr/bin/env sh
set -e

echo "==> Verificando e aplicando migrações de banco de dados..."
python database/scripts/migrate.py || {
    echo "AVISO: Falha ao rodar migrate.py automaticamente no startup. Prosseguindo com startup do servidor..."
}

echo "==> Iniciando Uvicorn..."
exec uvicorn backend.app.main:app --host 0.0.0.0 --port 8000

