"""Servicio de autenticación - hash de contraseñas, JWT, registro y login."""

from datetime import datetime, timedelta, timezone

import bcrypt
from jose import JWTError, jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.models.user import User
from app.schemas.auth import TokenPayload

# ── Configuración ──
_settings = get_settings()


# ────────────────────────────────────────────
# Funciones de hashing con bcrypt nativo
# ────────────────────────────────────────────

def hash_password(password: str) -> str:
    """Genera el hash bcrypt de una contraseña en texto plano."""
    pwd_bytes = password.encode("utf-8")[:72]  # Límite formal de especificación bcrypt
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(pwd_bytes, salt).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifica que una contraseña en texto plano coincida con su hash."""
    try:
        return bcrypt.checkpw(
            plain_password.encode("utf-8")[:72],
            hashed_password.encode("utf-8"),
        )
    except Exception:
        return False


# ────────────────────────────────────────────
# Funciones de JWT
# ────────────────────────────────────────────

def create_access_token(user_id: int) -> str:
    """Crea un JWT de acceso con expiración configurada."""
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=_settings.jwt_access_token_expire_minutes
    )
    payload = {"sub": str(user_id), "exp": expire, "type": "access"}
    return jwt.encode(payload, _settings.jwt_secret_key, algorithm=_settings.jwt_algorithm)


def create_refresh_token(user_id: int) -> str:
    """Crea un JWT de refresco con expiración extendida."""
    expire = datetime.now(timezone.utc) + timedelta(
        days=_settings.jwt_refresh_token_expire_days
    )
    payload = {"sub": str(user_id), "exp": expire, "type": "refresh"}
    return jwt.encode(payload, _settings.jwt_secret_key, algorithm=_settings.jwt_algorithm)


def decode_token(token: str) -> TokenPayload:
    """Decodifica y valida un JWT, retornando su payload tipado.

    Raises:
        JWTError: Si el token es inválido, expirado o malformado.
    """
    payload = jwt.decode(
        token,
        _settings.jwt_secret_key,
        algorithms=[_settings.jwt_algorithm],
    )
    return TokenPayload(sub=payload["sub"], exp=payload["exp"])


# ────────────────────────────────────────────
# Operaciones de usuario en BD
# ────────────────────────────────────────────

async def register_user(db: AsyncSession, user_create: "UserCreate") -> User:
    """Registra un nuevo usuario en la base de datos.

    Verifica que el email no esté registrado previamente.

    Args:
        db: Sesión asíncrona de la base de datos.
        user_create: Datos del nuevo usuario.

    Returns:
        La instancia del usuario creado.

    Raises:
        ValueError: Si el email ya está registrado.
    """
    from app.schemas.user import UserCreate  # noqa: F811 - import local para evitar circular

    # Verificar unicidad del email
    stmt = select(User).where(User.email == user_create.email)
    result = await db.execute(stmt)
    existing_user = result.scalar_one_or_none()

    if existing_user is not None:
        raise ValueError(f"El email '{user_create.email}' ya está registrado.")

    # Crear usuario con contraseña hasheada
    nuevo_usuario = User(
        email=user_create.email,
        hashed_password=hash_password(user_create.password),
        full_name=user_create.full_name,
        school=user_create.school,
        subject=user_create.subject,
    )
    db.add(nuevo_usuario)
    await db.flush()
    await db.refresh(nuevo_usuario)
    return nuevo_usuario


async def authenticate_user(
    db: AsyncSession, email: str, password: str
) -> User | None:
    """Autentica un usuario con email y contraseña.

    Args:
        db: Sesión asíncrona de la base de datos.
        email: Email del usuario.
        password: Contraseña en texto plano.

    Returns:
        La instancia del usuario si las credenciales son válidas, None en caso contrario.
    """
    stmt = select(User).where(User.email == email)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if user is None:
        return None

    if not verify_password(password, user.hashed_password):
        return None

    return user


async def get_user_by_id(db: AsyncSession, user_id: int) -> User | None:
    """Obtiene un usuario por su ID.

    Args:
        db: Sesión asíncrona de la base de datos.
        user_id: ID del usuario.

    Returns:
        La instancia del usuario o None si no existe.
    """
    stmt = select(User).where(User.id == user_id)
    result = await db.execute(stmt)
    return result.scalar_one_or_none()
