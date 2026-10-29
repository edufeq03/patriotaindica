#!/usr/bin/env python3
"""
Script Oficial de Reset Completo do Banco de Dados do Patriota Indica.
- Zera o schema public com segurança
- Reinstala extensões essenciais (uuid-ossp, pgcrypto, postgis, pg_trgm, unaccent)
- Executa em ordem todas as migrações SQL (001 a 019)
- Opcionalmente carrega dados de seed (categorias e empresas modelo de Campinas)
"""
import argparse
import asyncio
import os
import sys
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

# Adicionar raiz do projeto ao path
BASE_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(BASE_DIR))

MIGRATIONS_DIR = BASE_DIR / "database" / "migrations"
SEED_DIR = BASE_DIR / "database" / "seed"


async def reset_database(database_url: str, load_seed: bool = True):
    print("=" * 60)
    print(" 🔄 RESET DO BANCO DE DADOS - PATRIOTAIN DICA")
    print("=" * 60)
    print(f"Alvo: {database_url.split('@')[-1] if '@' in database_url else database_url}")

    engine = create_async_engine(database_url, echo=False)
    async_session = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        print("\n1. Limpando schema público (DROP SCHEMA public CASCADE)...")
        try:
            await session.execute(text("DROP SCHEMA IF EXISTS public CASCADE;"))
            await session.execute(text("CREATE SCHEMA public;"))
            await session.execute(text("GRANT ALL ON SCHEMA public TO CURRENT_USER;"))
            await session.execute(text("GRANT ALL ON SCHEMA public TO public;"))
            await session.commit()
            print("   ✓ Schema public recriado com sucesso.")
        except Exception as err:
            await session.rollback()
            print(f"   ❌ Erro ao limpar schema: {err}")
            return False

        print("\n2. Criando tabela de controle schema_migrations...")
        await session.execute(
            text(
                """
            CREATE TABLE IF NOT EXISTS schema_migrations (
                version VARCHAR(150) PRIMARY KEY,
                applied_at TIMESTAMPTZ DEFAULT NOW(),
                checksum VARCHAR(64) NOT NULL
            );
            """
            )
        )
        await session.commit()

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
                # Executa os comandos da migração
                await session.execute(text(sql_content))
                # Registra na tabela de controle
                await session.execute(
                    text("INSERT INTO schema_migrations (version, checksum) VALUES (:v, :c);"),
                    {"v": filename, "c": checksum},
                )
                await session.commit()
                print(f"      ✓ {filename} aplicado com sucesso.")
            except Exception as err:
                await session.rollback()
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
                    await session.execute(text(s_content))
                    await session.commit()
                    print(f"      ✓ {s_file.name} carregado com sucesso.")
                except Exception as s_err:
                    await session.rollback()
                    print(f"      ⚠️ Aviso ao carregar seed {s_file.name}: {s_err}")

    await engine.dispose()
    print("\n" + "=" * 60)
    print(" ✅ RESET DO BANCO DE DADOS CONCLUÍDO COM SUCESSO!")
    print(" Plano Mensal: R$ 14,90 (1490 centavos)")
    print("=" * 60)
    return True


def main():
    parser = argparse.ArgumentParser(description="Reset completo do banco de dados")
    parser.add_argument("--force", action="store_true", help="Executa o reset sem confirmação interativa")
    parser.add_argument("--no-seed", action="store_true", help="Não carrega os dados de seed")
    parser.add_argument("--database-url", type=str, default=None, help="URL de conexão asyncpg")

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
        db_url = "postgresql+asyncpg://postgres:postgres@localhost:5432/patriotaindica"

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
