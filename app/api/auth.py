"""Router de Autenticación (registro, login, perfil, refresh)."""

from fastapi import APIRouter, Depends, HTTPException, Response, status
from jose import JWTError
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.schemas.auth import LoginRequest, TokenResponse
from app.schemas.user import UserCreate, UserResponse, UserUpdate
from app.services.auth_service import (
    authenticate_user,
    create_access_token,
    create_refresh_token,
    decode_token,
    get_user_by_id,
    register_user,
)

router = APIRouter(prefix="/auth", tags=["Autenticación"])


@router.post(
    "/register",
    response_model=TokenResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Registrar nuevo usuario",
)
async def register(
    user_in: UserCreate,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    """Crea una nueva cuenta de profesor y retorna tokens de autenticación."""
    try:
        user = await register_user(db, user_in)
        await db.commit()
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e),
        )

    access_token = create_access_token(user.id)
    refresh_token = create_refresh_token(user.id)

    # Establecer cookie para navegación web
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        max_age=7200,
        samesite="lax",
    )

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
    )


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Iniciar sesión",
)
async def login(
    login_in: LoginRequest,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    """Verifica credenciales y retorna tokens JWT."""
    user = await authenticate_user(db, email=login_in.email, password=login_in.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciales incorrectas (email o contraseña no válidos).",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="La cuenta se encuentra inactiva.",
        )

    access_token = create_access_token(user.id)
    refresh_token = create_refresh_token(user.id)

    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        max_age=7200,
        samesite="lax",
    )

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
    )


@router.post(
    "/refresh",
    response_model=TokenResponse,
    summary="Renovar token de acceso",
)
async def refresh_token_endpoint(
    refresh_token: str,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    """Genera un nuevo access token a partir de un refresh token válido."""
    try:
        payload = decode_token(refresh_token)
        user_id = int(payload.sub)
    except (JWTError, ValueError, KeyError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token inválido o expirado.",
        )

    user = await get_user_by_id(db, user_id)
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuario no válido.",
        )

    new_access_token = create_access_token(user.id)
    new_refresh_token = create_refresh_token(user.id)

    response.set_cookie(
        key="access_token",
        value=new_access_token,
        httponly=True,
        max_age=7200,
        samesite="lax",
    )

    return TokenResponse(
        access_token=new_access_token,
        refresh_token=new_refresh_token,
        token_type="bearer",
    )


@router.get(
    "/me",
    response_model=UserResponse,
    summary="Perfil del usuario autenticado",
)
async def get_me(current_user: User = Depends(get_current_user)):
    """Retorna los datos del usuario logueado actualmente."""
    return current_user


@router.patch(
    "/me",
    response_model=UserResponse,
    summary="Actualizar perfil",
)
async def update_me(
    user_update: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Actualiza datos básicos del perfil (nombre, escuela, materia)."""
    if user_update.full_name is not None:
        current_user.full_name = user_update.full_name
    if user_update.school is not None:
        current_user.school = user_update.school
    if user_update.subject is not None:
        current_user.subject = user_update.subject

    await db.commit()
    await db.refresh(current_user)
    return current_user


@router.post(
    "/logout",
    summary="Cerrar sesión",
)
async def logout(response: Response):
    """Elimina la cookie de sesión."""
    response.delete_cookie(key="access_token")
    return {"message": "Sesión cerrada correctamente."}
