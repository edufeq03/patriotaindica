from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from backend.app.core.config import settings
from backend.app.core.database import get_db
from backend.app.core.security import (
    create_access_token,
    get_current_user,
    get_password_hash,
    verify_password,
)
from backend.app.models.user import User
from backend.app.schemas.triage import TokenResponse, UserCreate, UserOut

router = APIRouter()


@router.post("/login", response_model=TokenResponse)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db),
):
    """
    Login com email e senha para administradores e gestores.
    """
    stmt = select(User).where(User.email == form_data.username.lower().strip())
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if not user or not verify_password(form_data.password, user.password_hash):
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
async def register(payload: UserCreate, db: AsyncSession = Depends(get_db)):
    """
    Criação pública de usuário / gestor.
    SEGURANÇA: 'admin' NUNCA pode ser provisionado através deste endpoint público.
    """
    stmt = select(User).where(User.email == payload.email.lower().strip())
    exists = (await db.execute(stmt)).scalar_one_or_none()
    if exists:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Já existe uma conta cadastrada com este e-mail.",
        )

    # VULN-02 FIX: Cadastro público permite apenas 'user' ou 'owner'
    assigned_role = "owner" if payload.role == "owner" else "user"

    new_user = User(
        name=payload.name.strip(),
        email=payload.email.lower().strip(),
        password_hash=get_password_hash(payload.password),
        phone=payload.phone.strip() if payload.phone else None,
        role=assigned_role,
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
    Permite ao frontend validar a sessão e verificar seu papel ('admin' ou 'owner').
    """
    return current_user

