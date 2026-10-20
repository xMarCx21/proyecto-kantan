"""Dependencias comunes para endpoints de FastAPI."""

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.user import User
from app.services.auth_service import decode_token, get_user_by_id

# Soporte para header Authorization: Bearer <token>
security = HTTPBearer(auto_error=False)


async def get_current_user(
    request: Request,
    auth_credentials: HTTPAuthorizationCredentials | None = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Extrae y valida el usuario actual desde el token JWT.

    Busca el token en:
    1. Header `Authorization: Bearer <token>`
    2. Cookie `access_token` (para navegación en vistas HTML / Jinja2)

    Raises:
        HTTPException: Si el token falta, es inválido o el usuario no existe.
    """
    token: str | None = None

    # 1. Intentar desde Header
    if auth_credentials:
        token = auth_credentials.credentials
    # 2. Intentar desde Cookie
    elif "access_token" in request.cookies:
        token = request.cookies.get("access_token")

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No se encontró token de autenticación.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        payload = decode_token(token)
        user_id = int(payload.sub)
    except (JWTError, ValueError, KeyError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido o expirado.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = await get_user_by_id(db, user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuario no encontrado.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Usuario inactivo.",
        )

    return user


async def get_optional_current_user(
    request: Request,
    auth_credentials: HTTPAuthorizationCredentials | None = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> User | None:
    """Versión no estricta de get_current_user: retorna None si no está autenticado."""
    try:
        return await get_current_user(request, auth_credentials, db)
    except HTTPException:
        return None
