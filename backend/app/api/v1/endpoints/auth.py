from datetime import timedelta
from typing import Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.config import settings
from backend.app.core.database import get_db
from backend.app.core.rate_limit import check_rate_limit, get_client_ip
from backend.app.core.redis_client import (
    revoke_refresh_token,
    store_refresh_token,
    verify_and_revoke_refresh_token,
)
from backend.app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_refresh_token,
    get_current_user,
    get_password_hash,
    verify_password,
)
from backend.app.models.user import User
from backend.app.schemas.triage import (
    LogoutRequest,
    RefreshTokenRequest,
    TokenResponse,
    UserCreate,
    UserOut,
)

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
    - [H1, T2.3] Rate limit por IP (5/min) e por e-mail (10/hora) com fail-closed atômico.
    - [H8] Tempo de resposta constante (Dummy bcrypt execution) para evitar enumeração de contas.
    - [T2.1] Emissão de Access Token (15m) + Refresh Token rotativo (7d) persistido no Redis com jti.
    """
    client_ip = get_client_ip(request)
    email_clean = form_data.username.lower().strip()

    # Rate limiting estrito com fail-closed
    await check_rate_limit(
        key=f"ratelimit:login_ip:{client_ip}",
        limit=5,
        window_seconds=60,
        error_msg="Muitas tentativas de login a partir deste IP. Aguarde um minuto.",
        fail_closed=True,
    )
    await check_rate_limit(
        key=f"ratelimit:login_email:{email_clean}",
        limit=10,
        window_seconds=3600,
        error_msg="Muitas tentativas de login para este e-mail. Tente novamente mais tarde.",
        fail_closed=True,
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

    # 1. Access Token de curta duração (15 min)
    access_token = create_access_token(
        subject=user.id,
        role=user.role,
        expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
    )

    # 2. Refresh Token rotativo com jti único persistido no Redis
    refresh_token, jti, ttl_sec = create_refresh_token(
        subject=user.id,
        role=user.role,
    )
    await store_refresh_token(jti=jti, user_id=str(user.id), ttl_seconds=ttl_sec)

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "user": user,
    }


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token_endpoint(
    payload: RefreshTokenRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """
    Renovação de sessão com Rotação Atômica de Refresh Token (T2.1):
    - O refresh token antigo é invalidado imediatamente no Redis.
    - Um novo par (access_token + refresh_token) é emitido.
    - Se houver reutilização de token antigo, a renovação é sumariamente rejeitada.
    """
    client_ip = get_client_ip(request)
    await check_rate_limit(
        key=f"ratelimit:refresh_ip:{client_ip}",
        limit=30,
        window_seconds=60,
        error_msg="Muitas requisições de renovação de token. Aguarde.",
        fail_closed=True,
    )

    token_data = decode_refresh_token(payload.refresh_token)
    if not token_data or "sub" not in token_data or "jti" not in token_data:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token inválido ou expirado.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id_str = token_data["sub"]
    jti = token_data["jti"]

    # Rotação atômica: consome o jti do Redis
    is_valid = await verify_and_revoke_refresh_token(jti=jti, user_id=user_id_str)
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Sessão revogada ou refresh token já utilizado.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        user_uuid = UUID(user_id_str)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Identificador de usuário inválido.",
        )

    stmt = select(User).where(User.id == user_uuid)
    user = (await db.execute(stmt)).scalar_one_or_none()
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuário associado inativo ou não encontrado.",
        )

    # Gera novo par rotativo
    new_access_token = create_access_token(
        subject=user.id,
        role=user.role,
        expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
    )
    new_refresh_token, new_jti, new_ttl = create_refresh_token(
        subject=user.id,
        role=user.role,
    )
    await store_refresh_token(jti=new_jti, user_id=str(user.id), ttl_seconds=new_ttl)

    return {
        "access_token": new_access_token,
        "refresh_token": new_refresh_token,
        "token_type": "bearer",
        "user": user,
    }


@router.post("/logout")
async def logout(
    payload: Optional[LogoutRequest] = None,
):
    """
    Encerra a sessão revogando o Refresh Token no Redis (T2.1).
    """
    if payload and payload.refresh_token:
        token_data = decode_refresh_token(payload.refresh_token)
        if token_data and "jti" in token_data:
            await revoke_refresh_token(token_data["jti"])

    return {"detail": "Sessão encerrada com sucesso."}


@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
async def register(
    payload: UserCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """
    Criação pública de usuário.
    SEGURANÇA:
    - [H1, T2.3] Rate limit por IP (3/hora) com fail-closed.
    - [H8] Role 'admin' ou 'owner' NUNCA pode ser autoatribuída. Todos nascem como 'user'.
    - [H8] Verificação segura de unicidade de e-mail.
    """
    client_ip = get_client_ip(request)
    await check_rate_limit(
        key=f"ratelimit:register:{client_ip}",
        limit=3,
        window_seconds=3600,
        error_msg="Limite de cadastros por hora excedido para seu endereço IP.",
        fail_closed=True,
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
