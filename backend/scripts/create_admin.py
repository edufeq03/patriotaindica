"""
Script utilitário para provisionamento seguro do primeiro administrador.
Gera uma senha aleatória criptograficamente segura de uso único com exigência
de troca de senha no primeiro login.

Uso:
  python -m backend.scripts.create_admin --name "Nome Admin" --email admin@seudominio.com.br
"""

import argparse
import asyncio
import secrets
import sys
from sqlalchemy import select
from backend.app.core.database import async_session_factory
from backend.app.core.security import get_password_hash
from backend.app.models.user import User


async def create_admin(name: str, email: str, phone: str = None):
    email = email.lower().strip()
    name = name.strip()

    async with async_session_factory() as db:
        stmt = select(User).where(User.email == email)
        result = await db.execute(stmt)
        existing = result.scalar_one_or_none()

        if existing:
            print(f"[ERRO] Já existe um usuário cadastrado com o e-mail: {email}", file=sys.stderr)
            sys.exit(1)

        # Gera senha aleatória forte de 16 caracteres
        temp_password = secrets.token_urlsafe(16)
        password_hash = get_password_hash(temp_password)

        admin_user = User(
            name=name,
            email=email,
            phone=phone,
            password_hash=password_hash,
            role="admin",
            is_active=True,
            must_change_password=True,
        )

        db.add(admin_user)
        await db.commit()
        await db.refresh(admin_user)

        print("\n" + "=" * 70)
        print("  USUÁRIO ADMINISTRADOR PROVISIONADO COM SUCESSO!")
        print("=" * 70)
        print(f"  ID:       {admin_user.id}")
        print(f"  Nome:     {admin_user.name}")
        print(f"  E-mail:   {admin_user.email}")
        print(f"  Role:     {admin_user.role}")
        print(f"  Senha:    {temp_password}")
        print("-" * 70)
        print("  ATENÇÃO:")
        print("  1. Guarde esta senha em um cofre seguro (ex: 1Password, Bitwarden).")
        print("  2. Esta credencial NÃO será exibida novamente.")
        print("  3. A flag must_change_password foi ativada.")
        print("=" * 70 + "\n")


def main():
    parser = argparse.ArgumentParser(description="Criar conta de administrador do Patriota Indica")
    parser.add_argument("--name", required=True, help="Nome completo do administrador")
    parser.add_argument("--email", required=True, help="E-mail único de acesso")
    parser.add_argument("--phone", required=False, help="Telefone / WhatsApp (opcional)")

    args = parser.parse_args()
    asyncio.run(create_admin(args.name, args.email, args.phone))


if __name__ == "__main__":
    main()
