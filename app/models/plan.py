"""Modelo ORM - Plan Generado."""

from datetime import datetime

from sqlalchemy import ForeignKey, String, Text, Integer, DateTime, JSON, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


class GeneratedPlan(Base):
    """Plan diario generado a partir de una sesión de chat."""

    __tablename__ = "generated_plans"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    session_id: Mapped[int] = mapped_column(
        ForeignKey("chat_sessions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    plan_content: Mapped[dict] = mapped_column(JSON, nullable=False)
    docx_file_path: Mapped[str | None] = mapped_column(String(500), default=None)
    version: Mapped[int] = mapped_column(Integer, default=1)
    generated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # Relaciones
    session: Mapped["ChatSession"] = relationship(back_populates="generated_plans")  # noqa: F821

    def __repr__(self) -> str:
        return f"<GeneratedPlan id={self.id} session={self.session_id} v{self.version}>"
