"""Schemas Pydantic - Autenticación y JWT."""

from datetime import datetime

from pydantic import BaseModel, EmailStr


class LoginRequest(BaseModel):
    """Schema para solicitud de inicio de sesión."""

    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    """Schema de respuesta con tokens JWT."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class TokenPayload(BaseModel):
    """Schema del payload decodificado de un JWT."""

    sub: str
    exp: datetime
