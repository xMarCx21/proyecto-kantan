"""Schemas Pydantic - Chat (sesiones y mensajes)."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ChatSessionCreate(BaseModel):
    """Schema para crear una nueva sesión de chat."""

    title: str | None = None
    target_subject: str | None = None
    target_grade: str | None = None
    target_date: str | None = None
    document_ids: list[int] | None = Field(default=None)


class ChatSessionResponse(BaseModel):
    """Schema de respuesta para una sesión de chat."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    target_subject: str | None
    target_grade: str | None
    target_date: str | None
    created_at: datetime
    updated_at: datetime
    document_ids: list[int]
    message_count: int


class ChatMessageCreate(BaseModel):
    """Schema para enviar un mensaje del usuario."""

    content: str = Field(min_length=1)


class ChatMessageResponse(BaseModel):
    """Schema de respuesta para un mensaje de chat."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    role: str
    content: str
    created_at: datetime


class ChatSessionListResponse(BaseModel):
    """Schema de respuesta paginada de sesiones de chat."""

    sessions: list[ChatSessionResponse]
    total: int
