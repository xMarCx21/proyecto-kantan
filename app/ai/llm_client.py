"""Cliente para la API de Google Gemini."""

import asyncio
import logging
from collections.abc import AsyncGenerator

from google import genai
from google.genai import types

from app.config import get_settings

logger = logging.getLogger(__name__)

# Configuración de reintentos
_MAX_RETRIES = 3
_BASE_DELAY_SECONDS = 1.0


class GeminiClient:
    """Cliente asíncrono para interactuar con la API de Google Gemini.

    Proporciona métodos para generación de texto (normal y streaming)
    y generación de embeddings (individual y por lotes).
    """

    def __init__(self) -> None:
        """Inicializa el cliente de Gemini con la API key desde la configuración."""
        settings = get_settings()

        self._model = settings.gemini_model
        self._embedding_model = settings.embedding_model

        if not settings.gemini_api_key:
            logger.warning(
                "GEMINI_API_KEY no está configurada en .env. El cliente funcionará en modo demo."
            )
            self._client = None
        else:
            self._client = genai.Client(api_key=settings.gemini_api_key)
            logger.info("GeminiClient inicializado (modelo=%s)", self._model)

    async def _retry_with_backoff[T](
        self,
        operation: str,
        func,
        *args,
        **kwargs,
    ) -> T:
        """Ejecuta una función con reintentos y backoff exponencial.

        Args:
            operation: Nombre descriptivo de la operación (para logs).
            func: Función a ejecutar.
            *args: Argumentos posicionales.
            **kwargs: Argumentos con nombre.

        Returns:
            Resultado de la función.

        Raises:
            Exception: Si se agotan todos los reintentos.
        """
        last_error: Exception | None = None

        for attempt in range(1, _MAX_RETRIES + 1):
            try:
                return await asyncio.to_thread(func, *args, **kwargs)
            except Exception as e:
                last_error = e
                error_str = str(e).lower()

                # Errores que no deberían reintentarse
                if any(
                    term in error_str
                    for term in ["invalid_api_key", "permission_denied", "not_found"]
                ):
                    logger.error("Error no recuperable en %s: %s", operation, e)
                    raise

                delay = _BASE_DELAY_SECONDS * (2 ** (attempt - 1))
                logger.warning(
                    "%s - intento %d/%d fallido: %s. Reintentando en %.1fs...",
                    operation,
                    attempt,
                    _MAX_RETRIES,
                    e,
                    delay,
                )
                await asyncio.sleep(delay)

        logger.error("Todos los reintentos agotados para %s", operation)
        raise last_error  # type: ignore[misc]

    async def generate(
        self,
        prompt: str,
        system_instruction: str | None = None,
    ) -> str:
        """Genera una respuesta de texto completa.

        Args:
            prompt: Prompt del usuario.
            system_instruction: Instrucción de sistema opcional.

        Returns:
            Texto de la respuesta generada.
        """
        if self._client is None:
            return (
                "¡Hola! He recibido tu consulta pedagógica. "
                "Actualmente estoy funcionando en modo demostración local porque no se ha definido "
                "`GEMINI_API_KEY` en el archivo `.env`.\n\n"
                "Para habilitar el modelo Gemini en vivo, simplemente coloca tu clave en `.env`.\n\n"
                "Puedo generar y exportar el documento Word estructurado con tu secuencia didáctica."
            )

        config = types.GenerateContentConfig()
        if system_instruction:
            config.system_instruction = system_instruction

        def _call() -> str:
            response = self._client.models.generate_content(
                model=self._model,
                contents=prompt,
                config=config,
            )
            return response.text or ""

        resultado = await self._retry_with_backoff("generate", _call)
        logger.debug("Respuesta generada: %d caracteres", len(resultado))
        return resultado

    async def generate_stream(
        self,
        prompt: str,
        system_instruction: str | None = None,
    ) -> AsyncGenerator[str, None]:
        """Genera una respuesta de texto en streaming token por token."""
        if self._client is None:
            demo_text = (
                "¡Hola! He recibido tu instrucción pedagógica para armar la clase.\n\n"
                "*(Nota: Puedes colocar tu `GEMINI_API_KEY` en el archivo `.env` para consultar directamente al modelo Gemini en tiempo real)*.\n\n"
                "Aquí tienes una propuesta pedagógica adaptada:\n\n"
                "### 1. Objetivo de Aprendizaje\n"
                "Favorecer la apropiación de saberes mediante estrategias activas y trabajo colaborativo.\n\n"
                "### 2. Secuencia Didáctica Propuesta\n"
                "- **Inicio (10 min)**: Presentación del desafío inicial y recuperación de saberes previos.\n"
                "- **Desarrollo (30 min)**: Exposición dialogada, actividades prácticas guiadas y análisis grupal.\n"
                "- **Cierre (10 min)**: Síntesis de aprendizajes, resolución de dudas y rúbrica de autoevaluación.\n\n"
                "¡Haz clic en **'Descargar Word'** para obtener el documento oficial formateado!"
            )
            for word in demo_text.split(" "):
                await asyncio.sleep(0.03)
                yield word + " "
            return

        config = types.GenerateContentConfig()
        if system_instruction:
            config.system_instruction = system_instruction

        def _create_stream():
            return self._client.models.generate_content_stream(
                model=self._model,
                contents=prompt,
                config=config,
            )

        try:
            stream = await asyncio.to_thread(_create_stream)

            for chunk in stream:
                if chunk.text:
                    yield chunk.text

        except Exception as e:
            logger.error("Error en streaming: %s", e)
            raise

    async def generate_embedding(self, text: str) -> list[float]:
        """Genera un vector de embedding para un texto."""
        if not text or not text.strip():
            raise ValueError("El texto para embedding no puede estar vacío")

        if self._client is None:
            return [0.0] * 768

        def _call() -> list[float]:
            response = self._client.models.embed_content(
                model=self._embedding_model,
                contents=text,
            )
            return list(response.embeddings[0].values)

        return await self._retry_with_backoff("generate_embedding", _call)

    async def generate_embeddings_batch(
        self,
        texts: list[str],
    ) -> list[list[float]]:
        """Genera embeddings para un lote de textos."""
        if not texts:
            return []

        if self._client is None:
            return [[0.0] * 768 for _ in texts]

        # Filtrar textos vacíos pero mantener sus posiciones
        valid_indices = [i for i, t in enumerate(texts) if t and t.strip()]
        valid_texts = [texts[i] for i in valid_indices]

        if not valid_texts:
            raise ValueError("Todos los textos están vacíos")

        batch_size = 100
        all_embeddings: list[list[float]] = []

        for batch_start in range(0, len(valid_texts), batch_size):
            batch = valid_texts[batch_start:batch_start + batch_size]

            def _call(textos=batch) -> list[list[float]]:
                response = self._client.models.embed_content(
                    model=self._embedding_model,
                    contents=textos,
                )
                return [list(emb.values) for emb in response.embeddings]

            batch_embeddings = await self._retry_with_backoff(
                f"generate_embeddings_batch (lote {batch_start // batch_size + 1})",
                _call,
            )
            all_embeddings.extend(batch_embeddings)

        # Reconstruir la lista completa, con vectores vacíos para textos vacíos
        if len(valid_indices) == len(texts):
            return all_embeddings

        embedding_dim = len(all_embeddings[0]) if all_embeddings else 768
        resultado: list[list[float]] = [[0.0] * embedding_dim] * len(texts)
        for idx, emb_idx in enumerate(valid_indices):
            resultado[emb_idx] = all_embeddings[idx]

        return resultado

    def __repr__(self) -> str:
        return f"<GeminiClient model={self._model!r}>"
