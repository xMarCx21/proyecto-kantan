"""Plantillas de prompts para el asistente de planificación educativa."""

# ──────────────────────────────────────────────────────────────────────
# PROMPT DE SISTEMA PRINCIPAL
# ──────────────────────────────────────────────────────────────────────

SYSTEM_PROMPT = """\
Eres un experto planificador educativo argentino con amplia experiencia en diseño \
curricular y planificación de clases. Tu nombre es Kantan, el asistente de \
planificación docente.

## Tu Rol

- Asistes a docentes en la creación de planes diarios de clase.
- Utilizas el contexto de planes anteriores proporcionado para mantener coherencia \
y continuidad pedagógica.
- Generas planes estructurados con todos los apartados requeridos.
- Adaptas el nivel de complejidad según el grado/año indicado.
- Sigues los lineamientos curriculares vigentes.

## Directrices

1. **Siempre responde en español.**
2. Si el docente no proporciona información suficiente (materia, grado, tema, fecha), \
haz preguntas clarificadoras antes de generar un plan.
3. Cuando generes un plan, incluye TODOS los apartados: objetivo, contenidos, \
actividades de inicio/desarrollo/cierre, recursos, evaluación y observaciones.
4. Si se proporciona contexto de planes anteriores, úsalo para dar continuidad \
temática y evitar repeticiones.
5. Sé conciso pero completo. Prioriza la practicidad y aplicabilidad del plan.
6. Sugiere actividades variadas y dinámicas, adecuadas al nivel educativo.
7. Si el docente pide modificaciones, ajusta el plan sin perder la estructura.
"""

# ──────────────────────────────────────────────────────────────────────
# PLANTILLA DE CONTEXTO RAG
# ──────────────────────────────────────────────────────────────────────

RAG_CONTEXT_TEMPLATE = """\
## Contexto de Planes Anteriores

Los siguientes fragmentos provienen de documentos y planes previos del docente. \
Úsalos como referencia para mantener la coherencia y continuidad pedagógica:

{chunks}

---
Fin del contexto de referencia.
"""

# ──────────────────────────────────────────────────────────────────────
# PROMPT PARA GENERACIÓN DE PLAN ESTRUCTURADO (JSON)
# ──────────────────────────────────────────────────────────────────────

PLAN_GENERATION_PROMPT = """\
Genera un plan diario de clase completo y estructurado en formato JSON válido.

El JSON debe seguir EXACTAMENTE esta estructura (PlanDiario):

```json
{{
  "institucion": "Nombre de la institución educativa",
  "docente": "Nombre del docente",
  "materia": "Nombre de la materia/área",
  "grado": "Grado o año escolar",
  "fecha": "Fecha de la clase (YYYY-MM-DD)",
  "duracion_minutos": 80,
  "unidad_tematica": "Nombre de la unidad o eje temático",
  "tema": "Tema específico de la clase",
  "objetivos": [
    "Objetivo de aprendizaje 1",
    "Objetivo de aprendizaje 2"
  ],
  "contenidos": {{
    "conceptuales": ["Contenido conceptual 1"],
    "procedimentales": ["Contenido procedimental 1"],
    "actitudinales": ["Contenido actitudinal 1"]
  }},
  "actividades": {{
    "inicio": {{
      "descripcion": "Descripción de la actividad de inicio/motivación",
      "duracion_minutos": 15,
      "recursos": ["Recurso 1"]
    }},
    "desarrollo": {{
      "descripcion": "Descripción de la actividad principal de desarrollo",
      "duracion_minutos": 45,
      "recursos": ["Recurso 1"]
    }},
    "cierre": {{
      "descripcion": "Descripción de la actividad de cierre/síntesis",
      "duracion_minutos": 20,
      "recursos": ["Recurso 1"]
    }}
  }},
  "evaluacion": {{
    "tipo": "Formativa/Sumativa/Diagnóstica",
    "instrumentos": ["Instrumento de evaluación 1"],
    "criterios": ["Criterio de evaluación 1"]
  }},
  "recursos_generales": ["Recurso general 1"],
  "adaptaciones_curriculares": "Adaptaciones para necesidades educativas especiales (si aplica)",
  "observaciones": "Notas adicionales del docente",
  "tarea": "Descripción de la tarea para el hogar (si aplica)"
}}
```

IMPORTANTE:
- Responde ÚNICAMENTE con el JSON, sin texto adicional antes o después.
- No uses comentarios dentro del JSON.
- Asegúrate de que el JSON sea válido y parseable.
- Completa TODOS los campos con contenido relevante basado en la conversación.
- Si algún dato no fue proporcionado por el docente, usa valores razonables por defecto.

Datos proporcionados por el docente:
{user_context}
"""


def build_chat_prompt(
    system_prompt: str,
    rag_context: str | None,
    chat_history: list[dict],
    user_message: str,
) -> str:
    """Compone el prompt completo para el chat a partir de sus componentes.

    Construye un prompt unificado que incluye el contexto RAG,
    el historial de conversación y el mensaje actual del usuario.

    La instrucción de sistema se pasa por separado al modelo, por lo
    que no se incluye en el prompt retornado.

    Args:
        system_prompt: Instrucción de sistema (no se incluye en el retorno,
            se usa como referencia para la composición).
        rag_context: Contexto RAG formateado, o None si no hay contexto.
        chat_history: Lista de dicts con 'role' y 'content' representando
            el historial de la conversación.
        user_message: Mensaje actual del usuario.

    Returns:
        Prompt completo para enviar al modelo (sin la instrucción de sistema).
    """
    partes: list[str] = []

    # Agregar contexto RAG si existe
    if rag_context and rag_context.strip():
        partes.append(rag_context)

    # Agregar historial de conversación
    if chat_history:
        partes.append("## Historial de Conversación\n")
        for mensaje in chat_history:
            role = mensaje.get("role", "user")
            content = mensaje.get("content", "")

            if role == "user":
                partes.append(f"**Docente:** {content}")
            elif role == "assistant":
                partes.append(f"**Kantan:** {content}")
            elif role == "system":
                partes.append(f"**Sistema:** {content}")

        partes.append("")  # Línea en blanco después del historial

    # Agregar mensaje actual del usuario
    partes.append(f"**Docente:** {user_message}")

    return "\n\n".join(partes)
