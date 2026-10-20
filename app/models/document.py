"""Modelo ORM - Documento y Chunks."""

from datetime import datetime
from enum import StrEnum

from sqlalchemy import ForeignKey, String, Text, DateTime, Integer, JSON, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


class ProcessingStatus(StrEnum):
    """Estados de procesamiento de un documento."""
    PENDING = "pending"
    PROCESSING = "processing"
    PROCESSED = "processed"
    ERROR = "error"


class Document(Base):
    """Modelo de documento subido por un profesor."""

    __tablename__ = "documents"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    original_name: Mapped[str] = mapped_column(String(255), nullable=False)
    file_path: Mapped[str] = mapped_column(String(500), nullable=False)
    file_type: Mapped[str] = mapped_column(String(10), nullable=False)  # docx, pdf
    subject: Mapped[str | None] = mapped_column(String(255), default=None)
    grade_level: Mapped[str | None] = mapped_column(String(100), default=None)
    school_year: Mapped[int | None] = mapped_column(Integer, default=None)
    description: Mapped[str | None] = mapped_column(Text, default=None)
    processing_status: Mapped[str] = mapped_column(
        String(20), default=ProcessingStatus.PENDING
    )
    processing_error: Mapped[str | None] = mapped_column(Text, default=None)
    chunk_count: Mapped[int] = mapped_column(Integer, default=0)
    uploaded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # Relaciones
    owner: Mapped["User"] = relationship(back_populates="documents")  # noqa: F821
    chunks: Mapped[list["DocumentChunk"]] = relationship(
        back_populates="document", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Document id={self.id} name={self.original_name!r} status={self.processing_status}>"


class DocumentChunk(Base):
    """Fragmento de un documento para almacenamiento en vector store."""

    __tablename__ = "document_chunks"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    document_id: Mapped[int] = mapped_column(
        ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True
    )
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    embedding_id: Mapped[str] = mapped_column(String(255), nullable=False)
    chunk_metadata: Mapped[dict | None] = mapped_column("metadata", JSON, default=None)

    # Relaciones
    document: Mapped["Document"] = relationship(back_populates="chunks")

    def __repr__(self) -> str:
        return f"<DocumentChunk id={self.id} doc={self.document_id} idx={self.chunk_index}>"
