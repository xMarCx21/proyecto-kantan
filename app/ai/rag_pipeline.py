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
        """Genera o actualiza un plan diario estructurado en formato JSON con la IA."""
        import json
        import re
        from datetime import datetime

        rag_context = await self.retrieve_context(user_id, user_message, document_ids)
        hist_text = "\n".join(
            [f"{h.get('role', 'user')}: {h.get('content', '')}" for h in (chat_history or [])[-6:]]
        )

        prompt = f"""Eres Keyoku, asistente experto en diseño pedagógico y curricular.
Tu tarea es generar o actualizar un Plan Diario de Clase estructurado en formato JSON.

INSTRUCCIÓN DEL DOCENTE:
"{user_message}"

HISTORIAL RECIENTE:
{hist_text}

PLAN PREVIO A MODIFICAR (si existe, conserva todos sus campos y cambia ÚNICAMENTE lo que el docente solicita):
{json.dumps(current_plan, ensure_ascii=False) if current_plan else "No hay plan previo. Genera una planificación completa nueva."}

{rag_context if rag_context else ""}

INSTRUCCIONES ESTRICTAS:
1. Si el docente pide una modificación (por ejemplo: "cambia el docente a Prof. Marcelo López", "modifica el objetivo a...", "ajusta el tiempo a 80 minutos", "agrega recursos..."), modifica EXACTAMENTE ESE CAMPO. NUNCA pongas la instrucción del docente dentro del campo 'objetivo'. El 'objetivo' siempre debe ser una meta pedagógica (ej: "Comprender los procesos sociales y causas económicas...").
2. Si el docente indica su nombre (ej: "docente: Marcelo López" o "profesor Juan"), asígnalo al campo "docente".
3. Devuelve ÚNICAMENTE un objeto JSON válido (sin backticks, sin explicaciones adicionales) con esta estructura exacta:
{{
  "materia": "nombre de la materia o asignatura",
  "grado": "grado, año o nivel escolar",
  "docente": "nombre del docente o 'No especificado'",
  "institucion": "nombre de la institución educativa o 'Institución Educativa'",
  "fecha": "{datetime.now().strftime('%d/%m/%Y')}",
  "duracion_minutos": 60,
  "tema": "tema de la clase",
  "objetivo": "objetivo pedagógico claro y concreto",
  "contenidos": ["contenido 1", "contenido 2"],
  "inicio_desc": "apertura y recuperación de saberes previos",
  "inicio_duracion": 10,
  "inicio_actividades": ["actividad inicial 1"],
  "desarrollo_desc": "actividades centrales y desarrollo",
  "desarrollo_duracion": 40,
  "desarrollo_actividades": ["actividad de desarrollo 1", "actividad 2"],
  "cierre_desc": "síntesis y evaluación de cierre",
  "cierre_duracion": 10,
  "cierre_actividades": ["actividad de cierre"],
  "recursos": ["recurso 1", "recurso 2"],
  "evaluacion_tipo": "Formativa y Continua",
  "evaluacion_desc": "descripción de la evaluación",
  "evaluacion_criterios": ["criterio 1", "criterio 2"]
}}"""

        try:
            raw_response = await self.llm.generate(prompt, system_instruction=SYSTEM_PROMPT)
            cleaned = raw_response.strip()
            if "```json" in cleaned:
                cleaned = cleaned.split("```json")[1].split("```")[0].strip()
            elif "```" in cleaned:
                cleaned = cleaned.split("```")[1].split("```")[0].strip()

            parsed = json.loads(cleaned)
            # Asegurar que tenga todos los campos mínimos
            required_keys = ["materia", "grado", "docente", "tema", "objetivo"]
            if all(k in parsed for k in required_keys):
                return parsed
        except Exception as e:
            logger.warning("No se pudo parsear JSON directo de Gemini: %s", e)

        # Respaldo inteligente si falla la conexión de IA o formato
        fallback_plan = current_plan.copy() if current_plan else {
            "materia": "Planificación Docente",
            "grado": "Clase Diaria",
            "docente": "No especificado",
            "institucion": "Institución Educativa",
            "fecha": datetime.now().strftime("%d/%m/%Y"),
            "duracion_minutos": 60,
            "tema": user_message[:50],
            "objetivo": "Propiciar la apropiación significativa de los contenidos mediante actividades activas y colaborativas.",
            "contenidos": ["Conceptos nodales de la clase", "Estrategias de resolución", "Actividades prácticas"],
            "inicio_desc": "Recuperación de ideas previas y consigna disparadora inicial.",
            "inicio_duracion": 10,
            "inicio_actividades": ["Preguntas guía", "Debate introductorio"],
            "desarrollo_desc": "Trabajo activo en secuencias didácticas y resolución colaborativa.",
            "desarrollo_duracion": 40,
            "desarrollo_actividades": ["Ejercitación práctica", "Puesta en común por equipos"],
            "cierre_desc": "Evaluación formativa, resolución de dudas y ticket de salida.",
            "cierre_duracion": 10,
            "cierre_actividades": ["Síntesis final", "Rúbrica de autoevaluación"],
            "recursos": ["Material bibliográfico", "Pizarrón / Proyector", "Fichas de trabajo"],
            "evaluacion_tipo": "Formativa y Continua",
            "evaluacion_desc": "Monitoreo del desempeño y participación grupal.",
            "evaluacion_criterios": ["Comprensión conceptual", "Colaboración", "Entrega de actividades"],
        }

        # Extraer si el usuario pidió cambiar docente
        doc_match = re.search(r'(?:docente|profesor|profesora|nombre)\s*(?:es|sea|a|:)?\s*([A-Za-zÁÉÍÓÚáéíóúñÑ\s\.]+)', user_message, re.IGNORECASE)
        if doc_match:
            doc_val = doc_match.group(1).strip()
            # Limpiar conectores finales si hubiera
            doc_val = re.split(r'(?:y|en|con|para)', doc_val)[0].strip()
            if doc_val:
                fallback_plan["docente"] = doc_val

        # Extraer si el usuario pidió un tema específico
        if not current_plan and len(user_message.strip()) > 3:
            fallback_plan["tema"] = user_message[:60].strip()

        return fallback_plan
