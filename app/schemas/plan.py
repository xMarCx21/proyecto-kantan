"""Schemas Pydantic - Plan Diario generado."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ActividadSecuencia(BaseModel):
    """Bloque de una secuencia didáctica (inicio, desarrollo o cierre)."""

    duracion_minutos: int
    descripcion: str
    actividades: list[str]


class SecuenciaDidactica(BaseModel):
    """Secuencia didáctica completa con sus tres momentos."""

    inicio: ActividadSecuencia
    desarrollo: ActividadSecuencia
    cierre: ActividadSecuencia


class DatosGenerales(BaseModel):
    """Datos generales del plan de clase."""

    materia: str
    grado: str
    fecha: str
    duracion_minutos: int
    docente: str | None = None
    institucion: str | None = None


class Evaluacion(BaseModel):
    """Estrategia de evaluación del plan."""

    tipo: str
    descripcion: str
    criterios: list[str] | None = None


class PlanDiario(BaseModel):
    """Estructura completa de un plan diario de clase."""

    datos_generales: DatosGenerales
    objetivo: str
    contenidos: list[str]
    secuencia_didactica: SecuenciaDidactica
    recursos: list[str]
    evaluacion: Evaluacion


class PlanGeneratedResponse(BaseModel):
    """Schema de respuesta para un plan generado."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    session_id: int
    plan_content: PlanDiario
    version: int
    generated_at: datetime
    docx_download_url: str | None = None
