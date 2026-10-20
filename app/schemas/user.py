"""Schemas Pydantic - Usuario."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserCreate(BaseModel):
    """Schema para registro de un nuevo usuario."""

    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    full_name: str = Field(min_length=1, max_length=255)
    school: str | None = None
    subject: str | None = None


class UserUpdate(BaseModel):
    """Schema para actualización parcial del perfil."""

    full_name: str | None = Field(default=None, min_length=1, max_length=255)
    school: str | None = None
    subject: str | None = None


class UserResponse(BaseModel):
    """Schema de respuesta pública del usuario."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str
    full_name: str
    school: str | None
    subject: str | None
    is_active: bool
    created_at: datetime


class UserInDB(UserResponse):
    """Schema interno que incluye la contraseña hasheada."""

    hashed_password: str
