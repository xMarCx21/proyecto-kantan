"""Endpoints para subida y gestión de documentos históricos (.docx)."""

import os
import shutil
import uuid
from pathlib import Path
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.rag_pipeline import RAGPipeline
from app.config import get_settings
from app.db.session import get_db
from app.dependencies import get_current_user, get_optional_current_user
from app.models.document import Document
from app.models.user import User

router = APIRouter(prefix="/documents", tags=["Documentos"])
settings = get_settings()
pipeline = RAGPipeline()


@router.post("/upload", summary="Subir documento para contexto RAG")
async def upload_document(
    file: UploadFile = File(...),
    subject: str = Form(None),
    grade_level: str = Form(None),
    school_year: int = Form(None),
    description: str = Form(None),
    current_user: User | None = Depends(get_optional_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Sube un archivo .docx de un plan anterior, extrae su contenido y genera embeddings."""
    filename = file.filename or "documento.docx"
    ext = filename.split(".")[-1].lower()

    if ext not in ["docx", "txt", "pdf"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Solo se admiten archivos .docx o .txt por el momento.",
        )

    # Identificador de usuario o fallback temporal (para probar sin login estricto)
    user_id = current_user.id if current_user else 1

    # Asegurar que exista un usuario demo si no hay auth
    if not current_user:
        stmt = select(User).where(User.id == 1)
        res = await db.execute(stmt)
        if not res.scalar_one_or_none():
            demo_user = User(
                id=1,
                email="profesor.demo@kantan.edu",
                hashed_password="demo",
                full_name="Profesor Kantan",
                school="Colegio Modelo",
                subject="General",
            )
            db.add(demo_user)
            await db.commit()

    # Guardar archivo en disco
    safe_filename = f"{uuid.uuid4().hex}_{filename}"
    file_path = settings.upload_path / safe_filename

    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    # Registrar en base de datos
    doc = Document(
        user_id=user_id,
        filename=safe_filename,
        original_name=filename,
        file_path=str(file_path),
        file_type=ext,
        subject=subject or "General",
        grade_level=grade_level or "Todos",
        school_year=school_year,
        description=description,
        processing_status="processing",
    )
    db.add(doc)
    await db.commit()
    await db.refresh(doc)

    # Procesar en el pipeline RAG (extracción, chunking, embeddings)
    try:
        chunks_count = await pipeline.process_document(
            user_id=user_id,
            document_id=doc.id,
            file_path=str(file_path),
            file_type=ext,
            db=db,
        )
    except Exception as e:
        return {
            "id": doc.id,
            "filename": filename,
            "status": "warning",
            "message": f"El archivo se guardó, pero hubo un aviso al indexar: {e}",
            "chunks": 0,
        }

    return {
        "id": doc.id,
        "filename": filename,
        "status": "processed",
        "chunks": chunks_count,
        "message": f"Documento '{filename}' procesado e indexado correctamente.",
    }


@router.get("", summary="Listar documentos del docente")
async def list_documents(
    current_user: User | None = Depends(get_optional_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Retorna la lista de planes históricos disponibles para usar como contexto."""
    user_id = current_user.id if current_user else 1
    stmt = select(Document).where(Document.user_id == user_id).order_by(Document.uploaded_at.desc())
    res = await db.execute(stmt)
    docs = res.scalars().all()

    return [
        {
            "id": d.id,
            "original_name": d.original_name,
            "subject": d.subject,
            "grade_level": d.grade_level,
            "chunk_count": d.chunk_count,
            "processing_status": d.processing_status,
            "uploaded_at": d.uploaded_at.isoformat() if d.uploaded_at else None,
        }
        for d in docs
    ]
