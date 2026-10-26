from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.config import settings
from backend.app.core.database import get_db
from backend.app.core.rate_limit import check_rate_limit, get_client_ip
from backend.app.core.security import (
    create_access_token,
    get_current_user,
    get_password_hash,
    verify_password,
)
from backend.app.models.user import User
from backend.app.schemas.triage import TokenResponse, UserCreate, UserOut

router = APIRouter()

# Hash dummy pré-computado para mitigar timing attacks (H8)
DUMMY_BCRYPT_HASH = "$2b$12$e8YvXm/bQp4Q2rWzU9y8nOHrG2B9R6eQ2D5E1F4G7H9I1J3K5L7M9"


@router.post("/login", response_model=TokenResponse)
async def login(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db),
):
    """
    Login com email e senha para administradores e gestores.
    SEGURANÇA:
    - [H1] Rate limit por IP (5/min) e por e-mail (10/hora).
    - [H8] Tempo de resposta constante (Dummy bcrypt execution) para evitar enumeração de contas.
    """
    client_ip = get_client_ip(request)
    email_clean = form_data.username.lower().strip()

    # Rate limiting
    await check_rate_limit(
        key=f"ratelimit:login_ip:{client_ip}",
        limit=5,
        window_seconds=60,
        error_msg="Muitas tentativas de login a partir deste IP. Aguarde um minuto.",
    )
    await check_rate_limit(
        key=f"ratelimit:login_email:{email_clean}",
        limit=10,
        window_seconds=3600,
        error_msg="Muitas tentativas de login para este e-mail. Tente novamente mais tarde.",
    )

    stmt = select(User).where(User.email == email_clean)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    # Timing attack mitigation (H8): sempre roda o algoritmo bcrypt
    if user is None:
        verify_password(form_data.password, DUMMY_BCRYPT_HASH)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciais incorretas (e-mail ou senha inválidos).",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not verify_password(form_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciais incorretas (e-mail ou senha inválidos).",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Usuário inativo.",
        )

    access_token = create_access_token(
        subject=user.id,
        role=user.role,
        expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
    )

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": user,
    }


@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
async def register(
    payload: UserCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """
    Criação pública de usuário.
    SEGURANÇA:
    - [H1] Rate limit por IP (3/hora).
    - [H8] Role 'admin' ou 'owner' NUNCA pode ser autoatribuída. Todos nascem como 'user'.
    - [H8] Verificação segura de unicidade de e-mail.
    """
    client_ip = get_client_ip(request)
    await check_rate_limit(
        key=f"ratelimit:register:{client_ip}",
        limit=3,
        window_seconds=3600,
        error_msg="Limite de cadastros por hora excedido para seu endereço IP.",
    )

    clean_email = payload.email.lower().strip()
    stmt = select(User).where(User.email == clean_email)
    exists = (await db.execute(stmt)).scalar_one_or_none()
    if exists:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Não foi possível concluir o cadastro com as informações fornecidas.",
        )

    # Novo usuário público SEMPRE nasce como 'user'
    new_user = User(
        name=payload.name.strip(),
        email=clean_email,
        password_hash=get_password_hash(payload.password),
        phone=payload.phone.strip() if payload.phone else None,
        role="user",
    )
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)
    return new_user


@router.get("/me", response_model=UserOut)
async def get_current_user_profile(
    current_user: User = Depends(get_current_user),
):
    """
    Retorna os dados cadastrais do usuário autenticado via Bearer Token.
    """
    return current_user
