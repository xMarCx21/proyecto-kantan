"""Schemas Pydantic - Plan Diario y Ficha Pedagógica Oficial."""

from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field


class ActividadSecuencia(BaseModel):
    """Bloque de una secuencia didáctica (inicio, desarrollo o cierre)."""

    duracion_minutos: int = 15
    descripcion: str = ""
    actividades: list[str] = Field(default_factory=list)


class SecuenciaDidactica(BaseModel):
    """Secuencia didáctica completa con sus tres momentos."""

    inicio: ActividadSecuencia = Field(default_factory=ActividadSecuencia)
    desarrollo: ActividadSecuencia = Field(default_factory=ActividadSecuencia)
    cierre: ActividadSecuencia = Field(default_factory=ActividadSecuencia)


class DatosGenerales(BaseModel):
    """Datos generales del plan de clase."""

    materia: str = "Matemática"
    grado: str = "5° Grado"
    fecha: str = ""
    duracion_minutos: int = 80
    docente: str | None = None
    institucion: str | None = None
    mes: str | None = "Setiembre"
    ano: int | None = 2026


class Evaluacion(BaseModel):
    """Estrategia de evaluación del plan."""

    tipo: str = "Formativa"
    descripcion: str = "Registro de Secuencia de Aprendizaje (R.S.A.)"
    criterios: list[str] | None = None


class ProblemaPractico(BaseModel):
    """Problema práctico estructurado para el ejercitario de clase."""

    numero: int = 1
    enunciado: str
    datos: str = ""
    formula: str = ""
    solucion: str = ""
    respuesta: str = ""


class PlanDiario(BaseModel):
    """Estructura completa del Plan Diario y Ficha Práctica de Clase."""

    datos_generales: DatosGenerales
    objetivo: str
    contenidos: list[str] = Field(default_factory=list)
    secuencia_didactica: SecuenciaDidactica = Field(default_factory=SecuenciaDidactica)
    recursos: list[str] = Field(default_factory=list)
    evaluacion: Evaluacion = Field(default_factory=Evaluacion)

    # Campos de la estructura curricular oficial (MEC) y Ficha de Clase
    unidad_tematica: str = "El número y las operaciones"
    tema: str = ""
    capacidades: list[str] = Field(default_factory=list)
    indicadores: list[str] = Field(default_factory=list)
    momentos_didacticos_resumen: str = "Indagación previa, lectura de situación disparadora, deducción de fórmulas y resolución de ejercicios en el cuaderno."
    instrumento_evaluativo: str = "R.S.A."
    situacion_disparadora: str = ""
    conceptualizacion: str = ""
    problemas: list[ProblemaPractico] = Field(default_factory=list)
    ejercicios_aplicacion: list[str] = Field(default_factory=list)


class PlanGeneratedResponse(BaseModel):
    """Schema de respuesta para un plan generado."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    session_id: int
    plan_content: PlanDiario
    version: int
    generated_at: datetime
    docx_download_url: str | None = None
