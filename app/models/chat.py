"""Modelo ORM - Chat (sesiones y mensajes)."""

from datetime import datetime

from sqlalchemy import Column, ForeignKey, String, Text, DateTime, Table, JSON, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


# Tabla intermedia para la relación muchos-a-muchos entre sesiones y documentos
session_documents = Table(
    "session_documents",
    Base.metadata,
    Column("session_id", ForeignKey("chat_sessions.id", ondelete="CASCADE"), primary_key=True),
    Column("document_id", ForeignKey("documents.id", ondelete="CASCADE"), primary_key=True),
)


class ChatSession(Base):
    """Sesión de chat para la generación de un plan."""

    __tablename__ = "chat_sessions"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(255), default="Nueva sesión")
    target_subject: Mapped[str | None] = mapped_column(String(255), default=None)
    target_grade: Mapped[str | None] = mapped_column(String(100), default=None)
    target_date: Mapped[str | None] = mapped_column(String(20), default=None)
    system_instructions: Mapped[str | None] = mapped_column(Text, default=None)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relaciones
    owner: Mapped["User"] = relationship(back_populates="chat_sessions")  # noqa: F821
    messages: Mapped[list["ChatMessage"]] = relationship(
        back_populates="session", cascade="all, delete-orphan", order_by="ChatMessage.created_at"
    )
    context_documents: Mapped[list["Document"]] = relationship(  # noqa: F821
        secondary=session_documents
    )
    generated_plans: Mapped[list["GeneratedPlan"]] = relationship(  # noqa: F821
        back_populates="session", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<ChatSession id={self.id} title={self.title!r}>"


class ChatMessage(Base):
    """Mensaje individual dentro de una sesión de chat."""

    __tablename__ = "chat_messages"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    session_id: Mapped[int] = mapped_column(
        ForeignKey("chat_sessions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    role: Mapped[str] = mapped_column(String(20), nullable=False)  # user, assistant, system
    content: Mapped[str] = mapped_column(Text, nullable=False)
    msg_metadata: Mapped[dict | None] = mapped_column("metadata", JSON, default=None)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # Relaciones
    session: Mapped["ChatSession"] = relationship(back_populates="messages")

    def __repr__(self) -> str:
        return f"<ChatMessage id={self.id} role={self.role!r}>"
