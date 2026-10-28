#!/usr/bin/env python3
"""
Runner oficial de migrações SQL com controle de versão e detecção de drift (T6.1).
- Executa migrações de forma idempotente em ordem cronológica
- Registra cada arquivo aplicado na tabela 'schema_migrations' com hash SHA-256
- Detecta alterações acidentais em migrações já executadas (--check-drift)
"""
import argparse
import asyncio
import hashlib
import os
import sys
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

MIGRATIONS_DIR = Path(__file__).resolve().parent.parent / "migrations"


def get_file_checksum(filepath: Path) -> str:
    """Calcula o hash SHA-256 do conteúdo de um arquivo SQL."""
    sha256 = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(8192):
            sha256.update(chunk)
    return sha256.hexdigest()


async def init_schema_migrations_table(session: AsyncSession) -> None:
    """Garante a existência da tabela de controle schema_migrations."""
    create_table_sql = """
    CREATE TABLE IF NOT EXISTS schema_migrations (
        version VARCHAR(150) PRIMARY KEY,
        applied_at TIMESTAMPTZ DEFAULT NOW(),
        checksum VARCHAR(64) NOT NULL
    );
    """
    await session.execute(text(create_table_sql))
    await session.commit()


async def get_applied_migrations(session: AsyncSession) -> dict[str, str]:
    """Retorna um dicionário {version: checksum} das migrações já aplicadas."""
    query = text("SELECT version, checksum FROM schema_migrations ORDER BY version ASC;")
    result = await session.execute(query)
    return {row[0]: row[1] for row in result.fetchall()}


async def run_migrations(database_url: str, check_drift_only: bool = False, verbose: bool = True) -> int:
    engine = create_async_engine(database_url, echo=False)
    async_session = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

    sql_files = sorted(list(MIGRATIONS_DIR.glob("*.sql")))
    if not sql_files:
        if verbose:
            print(f"[AVISO] Nenhum arquivo SQL encontrado em {MIGRATIONS_DIR}")
        return 0

    drift_detected = False
    unapplied_count = 0

    async with async_session() as session:
        await init_schema_migrations_table(session)
        applied = await get_applied_migrations(session)

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
                        # Executa o script da migração
                        await session.execute(text(sql_content))
                        # Registra na tabela de controle
                        insert_sql = text(
                            "INSERT INTO schema_migrations (version, checksum) VALUES (:v, :c);"
                        )
                        await session.execute(insert_sql, {"v": filename, "c": current_checksum})
                        await session.commit()
                        print(f"  ✓ {filename} aplicado com sucesso.")
                    except Exception as err:
                        await session.rollback()
                        print(f"❌ Erro ao aplicar {filename}: {err}")
                        await engine.dispose()
                        return 1

    try:
        await engine.dispose()
    except (TypeError, AttributeError):
        pass

    if check_drift_only:
        if drift_detected or unapplied_count > 0:
            print("\n[FALHA] Validação de drift falhou: existem inconsistências ou migrações pendentes.")
            return 1
        print("\n[OK] Nenhuma divergência de esquema (drift) encontrada.")
        return 0

    print(f"\n[SUCESSO] Todas as migrações aplicadas. Total novas: {unapplied_count}")
    return 0



def main():
    parser = argparse.ArgumentParser(description="Runner de migrações e validação de drift para Patriota Indica.")
    parser.add_argument("--check-drift", action="store_true", help="Valida se há arquivos alterados ou pendentes sem aplicar.")
    parser.add_argument("--database-url", type=str, default=None, help="URL de conexão asyncpg (opcional, padrão do .env).")
    parser.add_argument("--quiet", action="store_true", help="Execução silenciosa.")

    args = parser.parse_args()

    db_url = args.database_url
    if not db_url:
        from backend.app.core.config import settings
        db_url = settings.DATABASE_URL

    exit_code = asyncio.run(run_migrations(database_url=db_url, check_drift_only=args.check_drift, verbose=not args.quiet))
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
