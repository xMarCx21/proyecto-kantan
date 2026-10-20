"""Interfaz con ChromaDB para almacenamiento y búsqueda de vectores."""

import logging

import chromadb
from chromadb import Collection

from app.config import get_settings

logger = logging.getLogger(__name__)


class VectorStore:
    """Gestiona colecciones de ChromaDB para almacenamiento vectorial por usuario.

    Cada usuario tiene su propia colección en ChromaDB para aislar
    los datos de sus documentos.
    """

    def __init__(self) -> None:
        """Inicializa el cliente persistente de ChromaDB."""
        settings = get_settings()
        self._client = chromadb.PersistentClient(path=settings.chroma_persist_dir)
        logger.info("VectorStore inicializado (persist_dir=%s)", settings.chroma_persist_dir)

    def get_or_create_collection(self, user_id: int) -> Collection:
        """Obtiene o crea una colección de ChromaDB para un usuario.

        Args:
            user_id: ID del usuario.

        Returns:
            Colección de ChromaDB asociada al usuario.
        """
        collection_name = f"user_{user_id}_docs"
        collection = self._client.get_or_create_collection(
            name=collection_name,
            metadata={"hnsw:space": "cosine"},
        )
        logger.debug("Colección obtenida/creada: %s", collection_name)
        return collection

    async def add_chunks(
        self,
        user_id: int,
        document_id: int,
        chunks: list[dict],
        embeddings: list[list[float]],
    ) -> None:
        """Almacena fragmentos de documento con sus embeddings en ChromaDB.

        Args:
            user_id: ID del usuario propietario.
            document_id: ID del documento al que pertenecen los chunks.
            chunks: Lista de dicts con 'content', 'chunk_index' y 'metadata'.
            embeddings: Lista de vectores de embedding correspondientes.

        Raises:
            ValueError: Si el número de chunks no coincide con el de embeddings.
        """
        if len(chunks) != len(embeddings):
            raise ValueError(
                f"Cantidad de chunks ({len(chunks)}) no coincide con "
                f"embeddings ({len(embeddings)})"
            )

        if not chunks:
            logger.warning("No hay chunks para almacenar (doc_id=%d)", document_id)
            return

        collection = self.get_or_create_collection(user_id)

        # Preparar datos para ChromaDB
        ids: list[str] = []
        documents: list[str] = []
        metadatas: list[dict] = []

        for chunk in chunks:
            chunk_id = f"doc_{document_id}_chunk_{chunk['chunk_index']}"
            ids.append(chunk_id)
            documents.append(chunk["content"])
            metadatas.append({
                "document_id": document_id,
                "chunk_index": chunk["chunk_index"],
                "char_start": chunk["metadata"].get("char_start", 0),
                "char_end": chunk["metadata"].get("char_end", 0),
            })

        # Insertar en ChromaDB (upsert para idempotencia)
        collection.upsert(
            ids=ids,
            embeddings=embeddings,
            documents=documents,
            metadatas=metadatas,
        )

        logger.info(
            "Almacenados %d chunks del documento %d para usuario %d",
            len(chunks),
            document_id,
            user_id,
        )

    async def search(
        self,
        user_id: int,
        query_embedding: list[float],
        document_ids: list[int],
        top_k: int = 10,
    ) -> list[dict]:
        """Busca fragmentos similares al query en los documentos especificados.

        Args:
            user_id: ID del usuario.
            query_embedding: Vector de embedding de la consulta.
            document_ids: Lista de IDs de documentos en los que buscar.
            top_k: Cantidad máxima de resultados a retornar.

        Returns:
            Lista de dicts con 'content', 'score', 'document_id' y 'chunk_index',
            ordenados por relevancia (mayor score = más similar).
        """
        if not document_ids:
            logger.warning("No se proporcionaron document_ids para búsqueda")
            return []

        collection = self.get_or_create_collection(user_id)

        # Verificar que la colección tiene datos
        if collection.count() == 0:
            logger.info("Colección vacía para usuario %d", user_id)
            return []

        # Construir filtro por document_ids
        if len(document_ids) == 1:
            where_filter = {"document_id": {"$eq": document_ids[0]}}
        else:
            where_filter = {"document_id": {"$in": document_ids}}

        try:
            results = collection.query(
                query_embeddings=[query_embedding],
                n_results=min(top_k, collection.count()),
                where=where_filter,
                include=["documents", "metadatas", "distances"],
            )
        except Exception as e:
            logger.error("Error en búsqueda ChromaDB: %s", e)
            return []

        # Convertir resultados al formato esperado
        resultados: list[dict] = []

        if not results or not results["documents"] or not results["documents"][0]:
            return resultados

        for i, doc_content in enumerate(results["documents"][0]):
            metadata = results["metadatas"][0][i] if results["metadatas"] else {}
            distance = results["distances"][0][i] if results["distances"] else 1.0

            # ChromaDB con cosine distance: distance = 1 - similarity
            # Convertir a score de similitud (0 a 1, mayor = más similar)
            score = max(0.0, 1.0 - distance)

            resultados.append({
                "content": doc_content,
                "score": score,
                "document_id": metadata.get("document_id", 0),
                "chunk_index": metadata.get("chunk_index", 0),
            })

        logger.debug(
            "Búsqueda para usuario %d: %d resultados de %d docs",
            user_id,
            len(resultados),
            len(document_ids),
        )

        return resultados

    async def delete_document_chunks(
        self,
        user_id: int,
        document_id: int,
    ) -> None:
        """Elimina todos los chunks de un documento de ChromaDB.

        Args:
            user_id: ID del usuario propietario.
            document_id: ID del documento cuyos chunks se eliminarán.
        """
        collection = self.get_or_create_collection(user_id)

        try:
            collection.delete(
                where={"document_id": {"$eq": document_id}},
            )
            logger.info(
                "Chunks eliminados del documento %d para usuario %d",
                document_id,
                user_id,
            )
        except Exception as e:
            logger.error(
                "Error al eliminar chunks del documento %d: %s",
                document_id,
                e,
            )
            raise

    def __repr__(self) -> str:
        return "<VectorStore (ChromaDB)>"
