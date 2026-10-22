"""Pipeline RAG (Retrieval-Augmented Generation) para Proyecto Kantan."""

import logging
from collections.abc import AsyncGenerator
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.llm_client import GeminiClient
from app.ai.prompts import SYSTEM_PROMPT, build_chat_prompt
from app.ai.vector_store import VectorStore
from app.document_processing.chunker import split_into_chunks
from app.document_processing.docx_parser import extract_from_docx
from app.document_processing.text_cleaner import clean_and_normalize
from app.models.document import Document, DocumentChunk

logger = logging.getLogger(__name__)


class RAGPipeline:
    """Orquesta la extracción, indexación y recuperación para generación de planes."""

    def __init__(self, llm_client: GeminiClient | None = None, vector_store: VectorStore | None = None):
        self.llm = llm_client or GeminiClient()
        self.vector_store = vector_store or VectorStore()

    async def process_document(
        self,
        user_id: int,
        document_id: int,
        file_path: str,
        file_type: str,
        db: AsyncSession,
    ) -> int:
        """Procesa un archivo .docx/.pdf: extrae, normaliza, fragmenta e indexa."""
        try:
            logger.info("Iniciando procesamiento de doc_id=%d (%s)", document_id, file_type)

            # 1. Extracción según formato
            if file_type.lower() == "docx":
                raw_text = extract_from_docx(file_path)
            else:
                # Fallback / texto plano
                with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                    raw_text = f.read()

            # 2. Limpieza y normalización
            clean_text = clean_and_normalize(raw_text)
            if not clean_text:
                raise ValueError("El documento no contiene texto extraíble.")

            # 3. Fragmentación (chunks)
            chunks = split_into_chunks(clean_text, chunk_size=800, overlap=100)
            if not chunks:
                raise ValueError("No se pudieron generar fragmentos del documento.")

            chunk_texts = [c["content"] for c in chunks]

            # 4. Generación de embeddings
            embeddings = await self.llm.generate_embeddings_batch(chunk_texts)

            # 5. Persistencia vectorial en ChromaDB
            await self.vector_store.add_chunks(
                user_id=user_id,
                document_id=document_id,
                chunks=chunks,
                embeddings=embeddings,
            )

            # 6. Registro de fragmentos en base de datos relacional
            for idx, c in enumerate(chunks):
                db_chunk = DocumentChunk(
                    document_id=document_id,
                    chunk_index=idx,
                    content=c["content"],
                    embedding_id=f"doc_{document_id}_chunk_{idx}",
                    chunk_metadata=c.get("metadata", {}),
                )
                db.add(db_chunk)

            # 7. Actualizar estado del documento
            stmt = select(Document).where(Document.id == document_id)
            res = await db.execute(stmt)
            doc = res.scalar_one_or_none()
            if doc:
                doc.processing_status = "processed"
                doc.chunk_count = len(chunks)

            await db.commit()
            logger.info("Documento doc_id=%d procesado exitosamente (%d chunks)", document_id, len(chunks))
            return len(chunks)

        except Exception as e:
            logger.error("Error al procesar documento doc_id=%d: %s", document_id, e)
            stmt = select(Document).where(Document.id == document_id)
            res = await db.execute(stmt)
            doc = res.scalar_one_or_none()
            if doc:
                doc.processing_status = "error"
                doc.processing_error = str(e)
                await db.commit()
            raise

    async def retrieve_context(
        self,
        user_id: int,
        query: str,
        document_ids: list[int] | None = None,
        top_k: int = 5,
    ) -> str:
        """Recupera fragmentos relevantes de planes anteriores para alimentar el prompt."""
        if not document_ids:
            return ""

        try:
            query_emb = await self.llm.generate_embedding(query)
            results = await self.vector_store.search(
                user_id=user_id,
                query_embedding=query_emb,
                document_ids=document_ids,
                top_k=top_k,
            )

            if not results:
                return ""

            context_pieces = [f"--- Referencia (Doc {r['document_id']}) ---\n{r['content']}" for r in results]
            return "\n\n".join(context_pieces)
        except Exception as e:
            logger.warning("No se pudo recuperar contexto RAG: %s", e)
            return ""

    async def chat_stream(
        self,
        user_id: int,
        user_message: str,
        document_ids: list[int] | None = None,
        chat_history: list[dict] | None = None,
    ) -> AsyncGenerator[str, None]:
        """Flujo conversacional con streaming de respuesta."""
        # 1. Recuperar contexto RAG si hay documentos seleccionados
        rag_context = await self.retrieve_context(user_id, user_message, document_ids)

        # 2. Componer prompt pedagógico
        full_prompt = build_chat_prompt(
            system_prompt=SYSTEM_PROMPT,
            rag_context=rag_context,
            chat_history=chat_history or [],
            user_message=user_message,
        )

        # 3. Stream desde el LLM
        async for chunk in self.llm.generate_stream(full_prompt, system_instruction=SYSTEM_PROMPT):
            yield chunk

    async def generate_structured_plan(
        self,
        user_id: int,
        user_message: str,
        document_ids: list[int] | None = None,
        chat_history: list[dict] | None = None,
        current_plan: dict | None = None,
    ) -> dict:
        """Genera o actualiza una planificación didáctica y ejercitario práctico completo (MEC Paraguay)."""
        import json
        import re
        from datetime import datetime

        rag_context = await self.retrieve_context(user_id, user_message, document_ids)
        hist_text = "\n".join(
            [f"{h.get('role', 'user')}: {h.get('content', '')}" for h in (chat_history or [])[-6:]]
        )

        prompt = f"""Eres Keyoku, planificador pedagógico oficial de la Educación Escolar Básica (MEC Paraguay).
Tu objetivo es generar o actualizar una PLANIFICACIÓN DIARIA OFICIAL COMPLETA JUNTO CON SU EJERCITARIO PRÁCTICO PARA EL AULA.

INSTRUCCIÓN DEL DOCENTE:
"{user_message}"

HISTORIAL DE LA CONVERSACIÓN:
{hist_text}

PLAN PREVIO A MODIFICAR (si existe, conserva todos sus campos y cambia ÚNICAMENTE lo que el docente solicita):
{json.dumps(current_plan, ensure_ascii=False) if current_plan else "No hay plan previo. Genera una planificación completa nueva."}

{rag_context if rag_context else ""}

INSTRUCCIONES CLAVE DE CONTENIDO Y ESTRUCTURA (MEC PARAGUAY):
1. **Curricular:** Incluye Área, Grado, Mes, Año, Tiempo, Unidad Temática, Tema, Capacidades oficiales, Indicadores observables y precisos, Momentos didácticos sintetizados e Instrumento evaluativo (por defecto: 'R.S.A.').
2. **Ficha de Clase y Ejercitario Práctico:**
   - **situacion_disparadora:** Situación o problema inicial contextualizado de la vida real (ej. compra en despensa, viaje escolar, terreno familiar, actividades deportivas) que despierta el interés.
   - **conceptualizacion:** Explicación teórica clara con fórmulas, definiciones y reglas clave ('Para saber / Para recordar').
   - **problemas:** Lista de 2 o 3 problemas prácticos contextualizados listos para que los alumnos resuelvan en el aula. Cada problema DEBE tener:
     - 'numero': entero
     - 'enunciado': texto del problema
     - 'datos': qué datos se extraen
     - 'formula': fórmula o esquema aplicable
     - 'solucion': desarrollo de los cálculos
     - 'respuesta': redacción completa de la respuesta
   - **ejercicios_aplicacion:** Lista de 2 o 3 ejercicios directos complementarios (conversiones de unidades, clasificaciones o cálculos directos).
3. **Modificaciones:** Si el docente pide cambiar el docente, tema, grado, etc., modifica únicamente ese campo y preserva el resto. NUNCA pongas la orden del usuario en el objetivo.
4. Devuelve ÚNICAMENTE un JSON válido (sin backticks, sin texto adicional) con esta estructura:
{{
  "materia": "nombre del área (ej. Matemática, Ciencias Naturales)",
  "grado": "grado escolar (ej. 5° Grado)",
  "mes": "Setiembre/Octubre",
  "ano": 2026,
  "docente": "nombre del docente o 'No especificado'",
  "institucion": "nombre de la institución educativa o 'Institución Educativa'",
  "fecha": "{datetime.now().strftime('%d/%m/%Y')}",
  "duracion_minutos": 80,
  "unidad_tematica": "El número y las operaciones / La geometría y la medida",
  "tema": "Tema específico de la clase",
  "objetivo": "Objetivo pedagógico claro",
  "capacidades": [
    "Comprende el problema enunciado.",
    "Identifica estrategias requeridas para la solución de problemas.",
    "Ejecuta el plan de solución aplicando fórmulas de resolución.",
    "Examina la solución obtenida y comunica la respuesta adecuadamente."
  ],
  "indicadores": [
    "Interpreta el enunciado del problema.",
    "Aplica correctamente las fórmulas y conceptos aprendidos.",
    "Opera sin error los algoritmos matemáticos requeridos.",
    "Comunica la respuesta considerando la unidad de medida correspondiente."
  ],
  "momentos_didacticos_resumen": "Observamos la situación disparadora inicial, analizamos información teórica, deducimos fórmulas en el pizarrón y resolvemos ejercicios en el cuaderno.",
  "instrumento_evaluativo": "R.S.A.",
  "situacion_disparadora": "Texto narrativo o problema cotidiano motivador para abrir la clase.",
  "conceptualizacion": "Definiciones y fórmulas destacadas para recordar y aplicar.",
  "problemas": [
    {{
      "numero": 1,
      "enunciado": "Enunciado del problema de la vida cotidiana...",
      "datos": "Datos extraídos...",
      "formula": "Fórmula aplicable...",
      "solucion": "Operaciones matemáticas...",
      "respuesta": "Respuesta completa..."
    }},
    {{
      "numero": 2,
      "enunciado": "Enunciado del segundo problema...",
      "datos": "Datos...",
      "formula": "Fórmula...",
      "solucion": "Operaciones...",
      "respuesta": "Respuesta..."
    }}
  ],
  "ejercicios_aplicacion": [
    "Ejercicio 1 de aplicación directa o conversión",
    "Ejercicio 2 de aplicación directa"
  ],
  "contenidos": ["Concepto fundamental", "Fórmulas y procedimientos", "Resolución de situaciones problemáticas"],
  "inicio_desc": "Presentación de la situación disparadora y recuperación de saberes previos.",
  "inicio_duracion": 15,
  "inicio_actividades": ["Lectura guiada de la situación inicial", "Lluvia de ideas y preguntas orientadoras"],
  "desarrollo_desc": "Conceptualización interactiva, deducción de fórmulas y modelado de ejemplos.",
  "desarrollo_duracion": 50,
  "desarrollo_actividades": ["Explicación en el pizarrón", "Resolución colaborativa de ejercicios guiados"],
  "cierre_desc": "Trabajo individual en el cuaderno, síntesis formativa y registro de indicadores.",
  "cierre_duracion": 15,
  "cierre_actividades": ["Resolución autónoma de los problemas", "Puesta en común y autoevaluación"],
  "recursos": ["Cuaderno del alumno", "Pizarrón y marcadores", "Fichas didácticas de trabajo", "Material concreto"],
  "evaluacion_tipo": "Formativa y Continua",
  "evaluacion_desc": "Registro de Secuencia de Aprendizaje (R.S.A.) mediante observación directa.",
  "evaluacion_criterios": ["Identificación de datos", "Uso correcto de algoritmos", "Comunicación de respuestas"]
}}
"""

        try:
            raw_response = await self.llm.generate(prompt, system_instruction=SYSTEM_PROMPT)
            cleaned = raw_response.strip()
            if "```json" in cleaned:
                cleaned = cleaned.split("```json")[1].split("```")[0].strip()
            elif "```" in cleaned:
                cleaned = cleaned.split("```")[1].split("```")[0].strip()

            parsed = json.loads(cleaned)
            required_keys = ["materia", "grado", "tema", "capacidades", "indicadores"]
            if any(k in parsed for k in required_keys):
                parsed.setdefault("unidad_tematica", "El número y las operaciones")
                parsed.setdefault("instrumento_evaluativo", "R.S.A.")
                parsed.setdefault("problemas", [])
                parsed.setdefault("ejercicios_aplicacion", [])
                parsed.setdefault("docente", "No especificado")
                parsed.setdefault("institucion", "Institución Educativa")
                parsed.setdefault("fecha", datetime.now().strftime("%d/%m/%Y"))
                parsed.setdefault("duracion_minutos", 80)
                parsed.setdefault("mes", "Setiembre/Octubre")
                parsed.setdefault("ano", 2026)
                return parsed
        except Exception as e:
            logger.warning("Fallo al consultar IA para plan estructurado: %s", e)

        # Generador pedagógico de respaldo enriquecido
        tema_sugerido = user_message[:60].strip() if len(user_message.strip()) > 3 else "Perímetro y Área de Figuras Planas"
        fallback = current_plan.copy() if current_plan else {
            "materia": "Matemática",
            "grado": "5° Grado",
            "mes": "Setiembre",
            "ano": 2026,
            "docente": "No especificado",
            "institucion": "Institución Educativa",
            "fecha": datetime.now().strftime("%d/%m/%Y"),
            "duracion_minutos": 80,
            "unidad_tematica": "El número y las operaciones / La geometría y la medida",
            "tema": tema_sugerido,
            "objetivo": f"Comprender, deducir y aplicar los conceptos fundamentales referentes a {tema_sugerido} en la resolución de situaciones problemáticas de la vida cotidiana.",
            "capacidades": [
                "Comprende el problema enunciado.",
                "Identifica estrategias requeridas para la solución de problemas.",
                "Ejecuta el plan de solución al problema planteado.",
                f"Examina la solución obtenida aplicando nociones de {tema_sugerido}.",
                "Lee, comprende y utiliza vocabulario y notación adecuados al contexto."
            ],
            "indicadores": [
                f"Interpreta la información referente a {tema_sugerido}.",
                "Determina la unidad fundamental y las fórmulas aplicables.",
                "Opera sin error los algoritmos matemáticos requeridos.",
                "Resuelve situaciones problemáticas aplicando los procedimientos aprendidos.",
                "Comunica la respuesta en forma coherente considerando la unidad de medida."
            ],
            "momentos_didacticos_resumen": "Observamos la situación disparadora inicial, analizamos la información teórica en el pizarrón, deducimos las fórmulas y resolvemos problemas en el cuaderno.",
            "instrumento_evaluativo": "R.S.A.",
            "situacion_disparadora": f"En la comunidad escolar se organizó una jornada deportiva y recreativa. Para acondicionar el patio, se necesita delimitar y calcular los espacios necesarios para las canchas y áreas verdes. Los estudiantes analizan las medidas y dimensiones para determinar los materiales que se deben utilizar.",
            "conceptualizacion": f"Para resolver situaciones problemáticas de {tema_sugerido}, identificamos los datos del problema, seleccionamos la fórmula o procedimiento correspondiente y realizamos las operaciones cuidando el orden de las unidades.",
            "problemas": [
                {
                    "numero": 1,
                    "enunciado": "Don Aurelio desea cercar un terreno rectangular de 35 metros de largo y 20 metros de ancho con 4 vueltas de alambre. ¿Cuántos metros de alambre necesitará comprar?",
                    "datos": "Largo = 35 m, Ancho = 20 m, Vueltas = 4",
                    "formula": "P = 2 x (Largo + Ancho); Total = P x 4",
                    "solucion": "P = 2 x (35 m + 20 m) = 2 x 55 m = 110 m\nTotal = 110 m x 4 = 440 m",
                    "respuesta": "Don Aurelio necesitará comprar 440 metros de alambre."
                },
                {
                    "numero": 2,
                    "enunciado": "Se desea colocar baldosas a una superficie cuadrangular de 15 metros de lado. ¿Cuál es el área total que será embaldosada en metros cuadrados?",
                    "datos": "Lado = 15 m",
                    "formula": "Área = Lado x Lado (A = l²)",
                    "solucion": "Área = 15 m x 15 m = 225 m²",
                    "respuesta": "La superficie total a embaldosar es de 225 m²."
                }
            ],
            "ejercicios_aplicacion": [
                "Expresa las medidas obtenidas en las unidades de conversión requeridas.",
                "Realiza el cálculo de verificación en tu cuaderno y contrasta tu resultado con tu compañero."
            ],
            "contenidos": [
                f"Conceptos y propiedades de {tema_sugerido}",
                "Deducción y aplicación de fórmulas",
                "Resolución y formulación de situaciones problemáticas"
            ],
            "inicio_desc": "Lectura y análisis de la situación disparadora, preguntas motivadoras y recuperación de saberes previos.",
            "inicio_duracion": 15,
            "inicio_actividades": ["Lectura grupal del problema disparador", "Identificación de ideas previas"],
            "desarrollo_desc": "Deducción de fórmulas y conceptos en el pizarrón con participación activa de los alumnos.",
            "desarrollo_duracion": 50,
            "desarrollo_actividades": ["Explicación dialogada", "Resolución guiada del primer problema modelo"],
            "cierre_desc": "Trabajo individual de resolución de problemas en el cuaderno y registro de indicadores de logro (R.S.A.).",
            "cierre_duracion": 15,
            "cierre_actividades": ["Resolución de ejercicios prácticos", "Puesta en común de resultados"],
            "recursos": ["Cuaderno de trabajo", "Pizarrón", "Regla, compás y cinta métrica", "Material fotocopiado"],
            "evaluacion_tipo": "Formativa y Continua",
            "evaluacion_desc": "Registro de Secuencia de Aprendizaje (R.S.A.) y lista de cotejo de desempeño.",
            "evaluacion_criterios": ["Identificación de datos", "Procedimiento algorítmico", "Respuesta contextualizada"]
        }

        # Extraer si el usuario pidió modificar docente
        doc_match = re.search(r'(?:docente|profesor|profesora|nombre)\s*(?:es|sea|a|:)?\s*([A-Za-zÁÉÍÓÚáéíóúñÑ\s\.]+)', user_message, re.IGNORECASE)
        if doc_match:
            doc_val = re.split(r'\b(?:y|en|con|para)\b', doc_match.group(1).strip())[0].strip()
            if doc_val:
                fallback["docente"] = doc_val

        # Extraer si el usuario pidió grado
        grado_match = re.search(r'([1-9]°?\s*(?:grado|año))', user_message, re.IGNORECASE)
        if grado_match:
            fallback["grado"] = grado_match.group(1).capitalize()

        return fallback
