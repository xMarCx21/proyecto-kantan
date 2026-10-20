"""Schemas Pydantic - Documento."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class DocumentUpload(BaseModel):
    """Metadata opcional al subir un documento."""

    subject: str | None = None
    grade_level: str | None = None
    school_year: int | None = None
    description: str | None = None


class DocumentResponse(BaseModel):
    """Schema de respuesta para un documento."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    filename: str
    original_name: str
    file_type: str
    subject: str | None
    grade_level: str | None
    school_year: int | None
    description: str | None
    processing_status: str
    processing_error: str | None
    chunk_count: int
    uploaded_at: datetime


class DocumentListResponse(BaseModel):
    """Schema de respuesta paginada de documentos."""

    documents: list[DocumentResponse]
    total: int
