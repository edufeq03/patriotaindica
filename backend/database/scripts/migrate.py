#!/usr/bin/env python3
"""
Runner oficial de migrações SQL com controle de versão e detecção de drift (T6.1).
- Executa migrações de forma idempotente em ordem cronológica via asyncpg (Simple Query Protocol)
- Registra cada arquivo aplicado na tabela 'schema_migrations' com hash SHA-256
- Detecta alterações acidentais em migrações já executadas (--check-drift)
"""
import argparse
import asyncio
import hashlib
import os
import sys
from pathlib import Path

import asyncpg

# Adicionar raiz do projeto ao path
BASE_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(BASE_DIR))

MIGRATIONS_DIR = BASE_DIR / "database" / "migrations"


def to_asyncpg_dsn(url: str) -> str:
    """Converte SQLAlchemy asyncpg URL para DSN padrão asyncpg."""
    if url.startswith("postgresql+asyncpg://"):
        return url.replace("postgresql+asyncpg://", "postgresql://", 1)
    return url


def get_file_checksum(filepath: Path) -> str:
    """Calcula o hash SHA-256 do conteúdo de um arquivo SQL."""
    sha256 = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(8192):
            sha256.update(chunk)
    return sha256.hexdigest()


async def run_migrations(database_url: str, check_drift_only: bool = False, verbose: bool = True) -> int:
    dsn = to_asyncpg_dsn(database_url)
    sql_files = sorted(list(MIGRATIONS_DIR.glob("*.sql")))
    if not sql_files:
        if verbose:
            print(f"[AVISO] Nenhum arquivo SQL encontrado em {MIGRATIONS_DIR}")
        return 0

    try:
        conn = await asyncpg.connect(dsn)
    except Exception as err:
        print(f"❌ Não foi possível conectar ao banco de dados: {err}")
        return 1

    try:
        # 1. Garante a existência da tabela schema_migrations
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS schema_migrations (
                version VARCHAR(150) PRIMARY KEY,
                applied_at TIMESTAMPTZ DEFAULT NOW(),
                checksum VARCHAR(64) NOT NULL
            );
        """)

        # 2. Carrega as migrações já aplicadas
        rows = await conn.fetch("SELECT version, checksum FROM schema_migrations ORDER BY version ASC;")
        applied = {row["version"]: row["checksum"] for row in rows}

        drift_detected = False
        unapplied_count = 0

        for filepath in sql_files:
            filename = filepath.name
            current_checksum = get_file_checksum(filepath)

            if filename in applied:
                recorded_checksum = applied[filename]
                if recorded_checksum != current_checksum:
                    drift_detected = True
                    print(f"❌ [DRIFT DETECTADO] {filename} foi alterado após ser aplicado!")
                    print(f"   Checksum gravado:  {recorded_checksum}")
                    print(f"   Checksum no disco: {current_checksum}")
                else:
                    if verbose:
                        print(f"✓ {filename} (já aplicado)")
            else:
                unapplied_count += 1
                if check_drift_only:
                    print(f"⚠️ [PENDENTE] {filename} ainda não foi aplicado.")
                else:
                    print(f"-> Aplicando: {filename}...")
                    with open(filepath, "r", encoding="utf-8") as f:
                        sql_content = f.read()

                    try:
                        # Executa o script da migração (suporta múltiplos comandos)
                        await conn.execute(sql_content)
                        # Registra na tabela de controle
                        await conn.execute(
                            "INSERT INTO schema_migrations (version, checksum) VALUES ($1, $2);",
                            filename,
                            current_checksum,
                        )
                        print(f"  ✓ {filename} aplicado com sucesso.")
                    except Exception as err:
                        print(f"❌ Erro ao aplicar {filename}: {err}")
                        return 1

        if check_drift_only:
            if drift_detected or unapplied_count > 0:
                print("\n[FALHA] Validação de drift falhou: existem inconsistências ou migrações pendentes.")
                return 1
            print("\n[OK] Nenhuma divergência de esquema (drift) encontrada.")
            return 0

        print(f"\n[SUCESSO] Todas as migrações aplicadas. Total novas: {unapplied_count}")
        return 0

    finally:
        await conn.close()


def main():
    parser = argparse.ArgumentParser(description="Runner de migrações e validação de drift para Patriota Indica.")
    parser.add_argument("--check-drift", action="store_true", help="Valida se há arquivos alterados ou pendentes sem aplicar.")
    parser.add_argument("--database-url", type=str, default=None, help="URL de conexão asyncpg (opcional, padrão do .env).")
    parser.add_argument("--quiet", action="store_true", help="Execução silenciosa.")

    args = parser.parse_args()

    db_url = args.database_url
    if not db_url:
        env_file = BASE_DIR / "backend" / ".env"
        if env_file.exists():
            with open(env_file, "r", encoding="utf-8") as f:
                for line in f:
                    if line.strip().startswith("DATABASE_URL="):
                        db_url = line.strip().split("=", 1)[1].strip().strip('"').strip("'")
                        break

    if not db_url:
        db_url = "postgresql://postgres:postgres@localhost:5432/patriotaindica"

    exit_code = asyncio.run(run_migrations(database_url=db_url, check_drift_only=args.check_drift, verbose=not args.quiet))
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
