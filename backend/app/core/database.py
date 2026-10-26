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
    """
    try:
        safe_user = user_id if user_id else ""
        safe_role = role if role else "anonymous"
        await session.execute(
            text("SET LOCAL app.user_id = :uid; SET LOCAL app.role = :role;"),
            {"uid": safe_user, "role": safe_role},
        )
    except Exception:
        # Em SQLite ou testes unitários sem suporte a SET LOCAL app.*, prossegue normalmente
        pass


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()

