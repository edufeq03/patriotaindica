#!/usr/bin/env python3
"""
Script Oficial de Reset Completo do Banco de Dados do Patriota Indica.
- Zera o schema public com segurança
- Reinstala extensões essenciais (uuid-ossp, pgcrypto, postgis, pg_trgm, unaccent)
- Executa em ordem todas as migrações SQL (001 a 019) usando Simple Query Protocol do asyncpg
- Opcionalmente carrega dados de seed (categorias e empresas modelo de Campinas)
"""
import argparse
import asyncio
import os
import sys
from pathlib import Path

import asyncpg

# Adicionar raiz do projeto ao path
BASE_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(BASE_DIR))

MIGRATIONS_DIR = BASE_DIR / "database" / "migrations"
SEED_DIR = BASE_DIR / "database" / "seed"


def to_asyncpg_dsn(url: str) -> str:
    """Converte SQLAlchemy asyncpg URL para DSN padrão asyncpg."""
    if url.startswith("postgresql+asyncpg://"):
        return url.replace("postgresql+asyncpg://", "postgresql://", 1)
    return url


async def reset_database(database_url: str, load_seed: bool = True) -> bool:
    print("=" * 60)
    print(" 🔄 RESET DO BANCO DE DADOS - PATRIOTAIN DICA")
    print("=" * 60)
    dsn = to_asyncpg_dsn(database_url)
    target_info = dsn.split("@")[-1] if "@" in dsn else dsn
    print(f"Alvo: {target_info}")

    try:
        conn = await asyncpg.connect(dsn)
    except Exception as err:
        print(f"❌ Não foi possível conectar ao banco de dados: {err}")
        return False

    try:
        print("\n1. Limpando schema público (DROP SCHEMA public CASCADE)...")
        await conn.execute("""
            DROP SCHEMA IF EXISTS public CASCADE;
            CREATE SCHEMA public;
            GRANT ALL ON SCHEMA public TO CURRENT_USER;
            GRANT ALL ON SCHEMA public TO public;
        """)
        print("   ✓ Schema public recriado com sucesso.")

        print("\n2. Criando tabela de controle schema_migrations...")
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS schema_migrations (
                version VARCHAR(150) PRIMARY KEY,
                applied_at TIMESTAMPTZ DEFAULT NOW(),
                checksum VARCHAR(64) NOT NULL
            );
        """)

        print("\n3. Aplicando migrações SQL...")
        from database.scripts.migrate import get_file_checksum

        sql_files = sorted(list(MIGRATIONS_DIR.glob("*.sql")))
        for filepath in sql_files:
            filename = filepath.name
            checksum = get_file_checksum(filepath)
            print(f"   -> Executando {filename}...")

            with open(filepath, "r", encoding="utf-8") as f:
                sql_content = f.read()

            try:
                # Executa múltiplos comandos sem prepared statement
                await conn.execute(sql_content)
                # Registra na tabela de controle
                await conn.execute(
                    "INSERT INTO schema_migrations (version, checksum) VALUES ($1, $2);",
                    filename,
                    checksum,
                )
                print(f"      ✓ {filename} aplicado com sucesso.")
            except Exception as err:
                print(f"      ❌ Erro ao aplicar {filename}: {err}")
                return False

        if load_seed and SEED_DIR.exists():
            print("\n4. Carregando dados iniciais de Seed...")
            seed_files = sorted(list(SEED_DIR.glob("*.sql")))
            for s_file in seed_files:
                print(f"   -> Carregando seed {s_file.name}...")
                with open(s_file, "r", encoding="utf-8") as f:
                    s_content = f.read()
                try:
                    await conn.execute(s_content)
                    print(f"      ✓ {s_file.name} carregado com sucesso.")
                except Exception as s_err:
                    print(f"      ⚠️ Aviso ao carregar seed {s_file.name}: {s_err}")

    finally:
        await conn.close()

    print("\n" + "=" * 60)
    print(" ✅ RESET DO BANCO DE DADOS CONCLUÍDO COM SUCESSO!")
    print(" Plano Mensal: R$ 14,90 (1490 centavos)")
    print("=" * 60)
    return True


def main():
    parser = argparse.ArgumentParser(description="Reset completo do banco de dados")
    parser.add_argument("--force", action="store_true", help="Executa o reset sem confirmação interativa")
    parser.add_argument("--no-seed", action="store_true", help="Não carrega os dados de seed")
    parser.add_argument("--database-url", type=str, default=None, help="URL de conexão asyncpg/postgresql")

    args = parser.parse_args()

    # Resolver DATABASE_URL
    db_url = args.database_url or os.getenv("DATABASE_URL")
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

    if not args.force:
        print("⚠️  ATENÇÃO: Todos os dados do banco serão apagados permanentemente!")
        confirm = input("Deseja realmente resetar o banco de dados? (digite 'sim' para continuar): ")
        if confirm.strip().lower() != "sim":
            print("Operação cancelada pelo usuário.")
            sys.exit(0)

    success = asyncio.run(reset_database(database_url=db_url, load_seed=not args.no_seed))
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
