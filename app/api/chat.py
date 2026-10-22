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
from app.export.template_manager import render_plan_to_docx
from app.models.user import User
from app.schemas.plan import (
    ActividadSecuencia,
    DatosGenerales,
    Evaluacion,
    PlanDiario,
    ProblemaPractico,
    SecuenciaDidactica,
)

router = APIRouter(prefix="/chat", tags=["Chat & Planes"])
pipeline = RAGPipeline()


class ChatMessageRequest(BaseModel):
    message: str
    document_ids: list[int] = []
    history: list[dict] = []


class GeneratePlanRequest(BaseModel):
    message: str
    document_ids: list[int] = []
    history: list[dict] = []
    current_plan: dict | None = None


class ExportPlanRequest(BaseModel):
    materia: str = "Matemática"
    grado: str = "5° Grado"
    docente: str = "No especificado"
    institucion: str = "Institución Educativa"
    fecha: str = ""
    duracion_minutos: int = 80
    mes: str = "Setiembre"
    ano: int = 2026
    unidad_tematica: str = "El número y las operaciones"
    tema: str = "Plan de Clase"
    objetivo: str = "Desarrollar y aplicar los conocimientos."
    capacidades: list[str] = []
    indicadores: list[str] = []
    momentos_didacticos_resumen: str = ""
    instrumento_evaluativo: str = "R.S.A."
    situacion_disparadora: str = ""
    conceptualizacion: str = ""
    problemas: list[dict] = []
    ejercicios_aplicacion: list[str] = []
    contenidos: list[str] = []
    inicio_desc: str = ""
    inicio_duracion: int = 15
    inicio_actividades: list[str] = []
    desarrollo_desc: str = ""
    desarrollo_duracion: int = 50
    desarrollo_actividades: list[str] = []
    cierre_desc: str = ""
    cierre_duracion: int = 15
    cierre_actividades: list[str] = []
    recursos: list[str] = []
    evaluacion_tipo: str = "Formativa"
    evaluacion_desc: str = "R.S.A."
    evaluacion_criterios: list[str] = []


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


@router.post("/generate-plan", summary="Generar o modificar plan estructurado con IA")
async def generate_plan(
    payload: GeneratePlanRequest,
    current_user: User | None = Depends(get_optional_current_user),
):
    """Genera o actualiza el plan pedagógico estructurado en JSON según la orden del docente."""
    user_id = current_user.id if current_user else 1
    plan_data = await pipeline.generate_structured_plan(
        user_id=user_id,
        user_message=payload.message,
        document_ids=payload.document_ids,
        chat_history=payload.history,
        current_plan=payload.current_plan,
    )
    return plan_data


@router.post("/export-docx", summary="Generar y descargar documento Word")
async def export_docx(
    payload: ExportPlanRequest,
    current_user: User | None = Depends(get_optional_current_user),
):
    """Convierte los datos estructurados del plan a un archivo .docx profesional.

    Si el docente ha configurado una plantilla institucional propia (con logo),
    la utiliza rellenando los campos directamente sobre ella.
    """
    user_id = current_user.id if current_user else 1
    try:
        # Mapear problemas estructurados
        problemas_objs = []
        for p in (payload.problemas or []):
            if isinstance(p, dict):
                problemas_objs.append(ProblemaPractico(**p))
            elif isinstance(p, ProblemaPractico):
                problemas_objs.append(p)

        plan = PlanDiario(
            datos_generales=DatosGenerales(
                materia=payload.materia,
                grado=payload.grado,
                fecha=payload.fecha or datetime.now().strftime("%d/%m/%Y"),
                duracion_minutos=payload.duracion_minutos or 80,
                docente=payload.docente or "No especificado",
                institucion=payload.institucion or "Institución Educativa",
                mes=payload.mes or "Setiembre",
                ano=payload.ano or 2026,
            ),
            unidad_tematica=payload.unidad_tematica or "El número y las operaciones",
            tema=payload.tema or payload.materia,
            objetivo=payload.objetivo,
            capacidades=payload.capacidades or [
                "Comprende el problema enunciado.",
                "Identifica estrategias requeridas para la solución de problemas.",
                "Ejecuta el plan de solución.",
                "Examina la solución obtenida y comunica la respuesta adecuadamente.",
            ],
            indicadores=payload.indicadores or [
                "Interpreta la información del problema.",
                "Aplica correctamente la fórmula o algoritmo.",
                "Opera sin error los cálculos requeridos.",
                "Comunica la respuesta considerando la unidad requerida.",
            ],
            momentos_didacticos_resumen=payload.momentos_didacticos_resumen or "Observamos situación inicial, conceptualizamos y resolvemos ejercicios en el cuaderno.",
            instrumento_evaluativo=payload.instrumento_evaluativo or "R.S.A.",
            situacion_disparadora=payload.situacion_disparadora or "",
            conceptualizacion=payload.conceptualizacion or "",
            problemas=problemas_objs,
            ejercicios_aplicacion=payload.ejercicios_aplicacion or [],
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
            recursos=payload.recursos or ["Cuaderno del alumno", "Pizarrón", "Fichas didácticas"],
            evaluacion=Evaluacion(
                tipo=payload.evaluacion_tipo or "Formativa",
                descripcion=payload.evaluacion_desc or "R.S.A.",
                criterios=payload.evaluacion_criterios or ["Identificación de datos", "Cálculo", "Respuesta"],
            ),
        )

        docx_buffer = render_plan_to_docx(plan, user_id=user_id)

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
