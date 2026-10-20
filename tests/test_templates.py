"""Pruebas para el gestor de plantillas institucionales de Word."""

import pytest
from app.export.template_manager import (
    create_base_model_template,
    render_plan_to_docx,
    save_user_template,
    remove_user_template,
)
from app.schemas.plan import (
    ActividadSecuencia,
    DatosGenerales,
    Evaluacion,
    PlanDiario,
    SecuenciaDidactica,
)


@pytest.fixture
def sample_plan():
    return PlanDiario(
        datos_generales=DatosGenerales(
            materia="Matemáticas",
            grado="4° Grado",
            fecha="20/10/2026",
            duracion_minutos=50,
            docente="Profesor Test",
            institucion="Colegio San Martín",
        ),
        objetivo="Comprender el concepto de fracciones equivalentes.",
        contenidos=["Fracciones propias", "Fracciones impropias"],
        secuencia_didactica=SecuenciaDidactica(
            inicio=ActividadSecuencia(
                duracion_minutos=10,
                descripcion="Activación de saberes previos.",
                actividades=["Pregunta disparadora"],
            ),
            desarrollo=ActividadSecuencia(
                duracion_minutos=30,
                descripcion="Resolución de problemas con material concreto.",
                actividades=["Trabajo en parejas"],
            ),
            cierre=ActividadSecuencia(
                duracion_minutos=10,
                descripcion="Puesta en común y cierre.",
                actividades=["Ticket de salida"],
            ),
        ),
        recursos=["Pizarrón", "Fichas"],
        evaluacion=Evaluacion(
            tipo="Formativa",
            descripcion="Observación del trabajo en clase.",
            criterios=["Participación", "Resolución correcta"],
        ),
    )


def test_create_base_model_template():
    """Verifica que la plantilla base se cree físicamente en disco."""
    path = create_base_model_template()
    assert path.exists()
    assert path.suffix == ".docx"


def test_render_plan_default(sample_plan):
    """Verifica que el generador produzca un buffer BytesIO válido sin plantilla custom."""
    buffer = render_plan_to_docx(sample_plan, user_id=999)
    assert buffer is not None
    assert buffer.getbuffer().nbytes > 1000


def test_render_plan_with_custom_template(sample_plan):
    """Verifica que renderice exitosamente sobre una plantilla con etiquetas docxtpl."""
    base_path = create_base_model_template()
    with open(base_path, "rb") as f:
        file_bytes = f.read()

    save_user_template(user_id=888, file_bytes=file_bytes, original_filename="Mi_Escuela.docx")
    
    buffer = render_plan_to_docx(sample_plan, user_id=888)
    assert buffer is not None
    assert buffer.getbuffer().nbytes > 1000

    # Limpieza
    remove_user_template(user_id=888)
