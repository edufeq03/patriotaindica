import logging
from sqlalchemy import func, select
from backend.app.core.config import settings
from backend.app.core.database import AsyncSessionLocal
from backend.app.core.security import get_password_hash
from backend.app.models.user import User

logger = logging.getLogger("patriotaindica")


async def ensure_admin() -> None:
    """
    Garante na inicializacao que o usuario admin especificado em ADMIN_EMAIL e ADMIN_PASSWORD
    exista no banco de dados com role='admin' e senha atualizada com bcrypt (A1 / S0).
    Neutraliza qualquer tentativa de pre-cadastro com o mesmo e-mail.
    """
    admin_email = (getattr(settings, "ADMIN_EMAIL", None) or "").strip().lower()
    admin_pass = getattr(settings, "ADMIN_PASSWORD", None)

    if not admin_email or not admin_pass:
        return

    admin_pass = str(admin_pass).strip()
    weak_passwords = {"admin123", "senha123", "password", "12345678", "admin", "123456"}
    if len(admin_pass) < 8 or admin_pass.lower() in weak_passwords:
        if settings.ENVIRONMENT == "production":
            logger.warning(
                "ADMIN_PASSWORD configurada e fraca ou previsivel. Em producao recomenda-se senha >= 12 caracteres."
            )

    try:
        async with AsyncSessionLocal() as db:
            stmt = select(User).where(func.lower(User.email) == admin_email)
            result = await db.execute(stmt)
            existing_user = result.scalar_one_or_none()

            pwd_hash = get_password_hash(admin_pass)

            if existing_user is None:
                new_admin = User(
                    name="Administrador Curador",
                    email=admin_email,
                    role="admin",
                    password_hash=pwd_hash,
                    is_active=True,
                )
                db.add(new_admin)
                await db.commit()
                logger.info("Admin inicializado no banco com sucesso [%s].", admin_email)
            else:
                existing_user.role = "admin"
                existing_user.password_hash = pwd_hash
                existing_user.is_active = True
                await db.commit()
                logger.info("Admin existente atualizado e promovido no banco [%s].", admin_email)
    except Exception as exc:
        logger.warning("Nao foi possivel executar ensure_admin na inicializacao (banco indisponivel ou tabelas ausentes): %s", exc)

