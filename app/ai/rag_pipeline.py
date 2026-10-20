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
