from typing import AsyncGenerator
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import declarative_base
from backend.app.core.config import settings

engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
    future=True,
    pool_pre_ping=True,
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,
)

async_session_factory = AsyncSessionLocal

Base = declarative_base()


async def set_db_app_context(session: AsyncSession, user_id: str = None, role: str = None) -> None:
    """
    Define os parâmetros de sessão da transação no PostgreSQL para aplicação do RLS:
    current_setting('app.user_id') e current_setting('app.role').
    Falha fechada (fail-closed, 500) se não conseguir aplicar o contexto de segurança no banco de dados.
    """
    safe_user = str(user_id) if user_id else ""
    safe_role = str(role) if role else "anonymous"
    try:
        await session.execute(
            text("SELECT set_config('app.user_id', :uid, true), set_config('app.role', :role, true);"),
            {"uid": safe_user, "role": safe_role},
        )
    except Exception as exc:
        bind = getattr(session, "bind", None)
        dialect_name = getattr(getattr(bind, "dialect", None), "name", None)
        if dialect_name == "sqlite":
            return
        import logging
        from fastapi import HTTPException, status
        logging.getLogger("patriotaindica").error(
            "Falha ao definir contexto RLS de banco de dados [user=%s, role=%s]: %s", safe_user, safe_role, exc
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Falha ao inicializar contexto de segurança da sessão.",
        )


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()

