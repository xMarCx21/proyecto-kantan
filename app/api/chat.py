"""Endpoints para interacción de chat pedagógico y exportación a Word."""

import io
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse

from app.ai.rag_pipeline import RAGPipeline
from app.dependencies import get_optional_current_user
from app.export.docx_builder import PlanDocxBuilder
from app.models.user import User
from app.schemas.plan import (
    ActividadSecuencia,
    DatosGenerales,
    Evaluacion,
    PlanDiario,
    SecuenciaDidactica,
)

router = APIRouter(prefix="/chat", tags=["Chat & Planes"])
pipeline = RAGPipeline()


class ChatMessageRequest(BaseModel):
    message: str
    document_ids: list[int] = []
    history: list[dict] = []


class ExportPlanRequest(BaseModel):
    materia: str = "Matemáticas"
    grado: str = "4° Grado"
    tema: str = "Plan de Clase"
    objetivo: str = "Desarrollar comprensión de los contenidos."
    contenidos: list[str] = ["Conceptos fundamentales", "Aplicación práctica"]
    inicio_desc: str = "Recuperación de conocimientos previos y activación."
    inicio_duracion: int = 10
    inicio_actividades: list[str] = ["Preguntas disparadoras", "Lluvia de ideas"]
    desarrollo_desc: str = "Explicación interactiva y ejercitación guiada."
    desarrollo_duracion: int = 30
    desarrollo_actividades: list[str] = ["Trabajo en equipos", "Resolución de problemas"]
    cierre_desc: str = "Puesta en común, síntesis y evaluación rápida."
    cierre_duracion: int = 10
    cierre_actividades: list[str] = ["Ticket de salida", "Preguntas de metacognición"]
    recursos: list[str] = ["Pizarrón", "Cuaderno", "Guía de actividades"]
    evaluacion_tipo: str = "Formativa"
    evaluacion_desc: str = "Observación directa y retroalimentación continua."
    evaluacion_criterios: list[str] = ["Participación activa", "Resolución adecuada"]


@router.post("/stream", summary="Chat con IA y streaming de tokens")
async def chat_stream(
    payload: ChatMessageRequest,
    current_user: User | None = Depends(get_optional_current_user),
):
    """Envía un mensaje a Kantan y hace streaming de la respuesta pedagógica."""
    user_id = current_user.id if current_user else 1

    async def event_generator():
        async for chunk in pipeline.chat_stream(
            user_id=user_id,
            user_message=payload.message,
            document_ids=payload.document_ids,
            chat_history=payload.history,
        ):
            yield {"data": chunk}

    return EventSourceResponse(event_generator())


@router.post("/export-docx", summary="Generar y descargar documento Word")
async def export_docx(payload: ExportPlanRequest):
    """Convierte los datos estructurados del plan a un archivo .docx profesional."""
    try:
        plan = PlanDiario(
            datos_generales=DatosGenerales(
                materia=payload.materia,
                grado=payload.grado,
                fecha=datetime.now().strftime("%d/%m/%Y"),
                duracion_minutos=payload.inicio_duracion + payload.desarrollo_duracion + payload.cierre_duracion,
                docente="Docente",
                institucion="Institución Educativa",
            ),
            objetivo=payload.objetivo,
            contenidos=payload.contenidos or [payload.tema],
            secuencia_didactica=SecuenciaDidactica(
                inicio=ActividadSecuencia(
                    duracion_minutos=payload.inicio_duracion,
                    descripcion=payload.inicio_desc,
                    actividades=payload.inicio_actividades,
                ),
                desarrollo=ActividadSecuencia(
                    duracion_minutos=payload.desarrollo_duracion,
                    descripcion=payload.desarrollo_desc,
                    actividades=payload.desarrollo_actividades,
                ),
                cierre=ActividadSecuencia(
                    duracion_minutos=payload.cierre_duracion,
                    descripcion=payload.cierre_desc,
                    actividades=payload.cierre_actividades,
                ),
            ),
            recursos=payload.recursos,
            evaluacion=Evaluacion(
                tipo=payload.evaluacion_tipo,
                descripcion=payload.evaluacion_desc,
                criterios=payload.evaluacion_criterios,
            ),
        )

        builder = PlanDocxBuilder()
        docx_buffer = builder.build(plan)

        filename = f"Plan_Diario_{payload.materia.replace(' ', '_')}.docx"

        return StreamingResponse(
            docx_buffer,
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al generar el documento: {e}",
        )
