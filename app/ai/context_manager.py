"""Gestión de la ventana de contexto y conteo de tokens."""

import logging

import tiktoken

logger = logging.getLogger(__name__)

# Encoding compatible con los modelos Gemini (aproximación con cl100k_base)
_ENCODING_NAME = "cl100k_base"


class ContextWindowManager:
    """Gestiona el presupuesto de tokens para construir prompts.

    Se asegura de que el prompt total no exceda la ventana de contexto,
    priorizando componentes en este orden:
    1. Instrucción de sistema (siempre incluida)
    2. Mensaje actual del usuario (siempre incluido)
    3. Chunks RAG (truncados si es necesario)
    4. Historial de chat (truncado desde los más antiguos)
    """

    MAX_CONTEXT_TOKENS = 28_000

    def __init__(self) -> None:
        """Inicializa el gestor con el encoding de tokens."""
        try:
            self._encoding = tiktoken.get_encoding(_ENCODING_NAME)
        except Exception:
            logger.warning(
                "No se pudo cargar el encoding %s. Usando estimación por caracteres.",
                _ENCODING_NAME,
            )
            self._encoding = None

    def count_tokens(self, text: str) -> int:
        """Cuenta la cantidad de tokens en un texto.

        Usa tiktoken con el encoding cl100k_base. Si no está disponible,
        estima 1 token ≈ 4 caracteres.

        Args:
            text: Texto del cual contar tokens.

        Returns:
            Cantidad estimada de tokens.
        """
        if not text:
            return 0

        if self._encoding is not None:
            return len(self._encoding.encode(text))

        # Estimación de respaldo: ~4 caracteres por token
        return len(text) // 4

    def _truncate_text(self, text: str, max_tokens: int) -> str:
        """Trunca un texto a un máximo de tokens.

        Args:
            text: Texto a truncar.
            max_tokens: Máximo de tokens permitidos.

        Returns:
            Texto truncado (o el original si cabe).
        """
        if not text or max_tokens <= 0:
            return ""

        current_tokens = self.count_tokens(text)
        if current_tokens <= max_tokens:
            return text

        if self._encoding is not None:
            tokens = self._encoding.encode(text)
            truncated_tokens = tokens[:max_tokens]
            return self._encoding.decode(truncated_tokens)

        # Estimación: ~4 chars por token
        max_chars = max_tokens * 4
        truncated = text[:max_chars]
        # Intentar cortar en un espacio
        last_space = truncated.rfind(" ")
        if last_space > max_chars * 0.8:
            truncated = truncated[:last_space]
        return truncated + "\n\n[... contenido truncado por límite de tokens ...]"

    def _truncate_chat_history(
        self,
        chat_history: list[dict],
        max_tokens: int,
    ) -> list[dict]:
        """Trunca el historial de chat manteniendo los mensajes más recientes.

        Args:
            chat_history: Lista de mensajes con 'role' y 'content'.
            max_tokens: Máximo de tokens para el historial completo.

        Returns:
            Historial truncado (mensajes más recientes primero).
        """
        if not chat_history or max_tokens <= 0:
            return []

        # Construir desde el final (más reciente) hacia el inicio
        resultado: list[dict] = []
        tokens_usados = 0

        for mensaje in reversed(chat_history):
            content = mensaje.get("content", "")
            role = mensaje.get("role", "user")
            # Formato del mensaje en el prompt
            msg_text = f"**{role.capitalize()}:** {content}"
            msg_tokens = self.count_tokens(msg_text)

            if tokens_usados + msg_tokens > max_tokens:
                break

            resultado.insert(0, mensaje)
            tokens_usados += msg_tokens

        return resultado

    def build_prompt(
        self,
        system_prompt: str,
        rag_chunks: str | None,
        chat_history: list[dict],
        user_message: str,
    ) -> tuple[str, str]:
        """Construye el prompt optimizado dentro del límite de tokens.

        Prioriza la inclusión de componentes en este orden:
        1. Instrucción de sistema → siempre completa
        2. Mensaje del usuario → siempre completo
        3. Contexto RAG → truncado si es necesario
        4. Historial de chat → truncado desde los más antiguos

        Args:
            system_prompt: Instrucción de sistema para el modelo.
            rag_chunks: Contexto RAG formateado, o None.
            chat_history: Historial de conversación.
            user_message: Mensaje actual del usuario.

        Returns:
            Tupla (system_instruction, user_prompt) lista para enviar al modelo.
        """
        # ── 1. Calcular tokens fijos (sistema + mensaje del usuario) ──
        system_tokens = self.count_tokens(system_prompt)
        user_msg_text = f"**Docente:** {user_message}"
        user_tokens = self.count_tokens(user_msg_text)

        tokens_fijos = system_tokens + user_tokens
        tokens_disponibles = self.MAX_CONTEXT_TOKENS - tokens_fijos

        if tokens_disponibles <= 0:
            # El sistema + usuario ya exceden el límite; truncar el mensaje del usuario
            logger.warning(
                "System prompt + user message exceden el límite (%d tokens). "
                "Truncando mensaje del usuario.",
                tokens_fijos,
            )
            available_for_user = self.MAX_CONTEXT_TOKENS - system_tokens - 100
            user_message = self._truncate_text(user_message, max(available_for_user, 100))
            user_msg_text = f"**Docente:** {user_message}"
            user_tokens = self.count_tokens(user_msg_text)
            tokens_disponibles = 0

        # ── 2. Asignar presupuesto a RAG y historial ──
        # 60% del espacio disponible para RAG, 40% para historial
        rag_budget = int(tokens_disponibles * 0.6)
        history_budget = tokens_disponibles - rag_budget

        # ── 3. Procesar contexto RAG ──
        rag_text = ""
        if rag_chunks and rag_chunks.strip():
            rag_tokens = self.count_tokens(rag_chunks)
            if rag_tokens <= rag_budget:
                rag_text = rag_chunks
                # Dar el espacio sobrante al historial
                history_budget += rag_budget - rag_tokens
            else:
                rag_text = self._truncate_text(rag_chunks, rag_budget)
                logger.info(
                    "Contexto RAG truncado de %d a %d tokens",
                    rag_tokens,
                    rag_budget,
                )

        # ── 4. Procesar historial de chat ──
        truncated_history = self._truncate_chat_history(chat_history, history_budget)

        if len(truncated_history) < len(chat_history):
            logger.info(
                "Historial de chat truncado de %d a %d mensajes",
                len(chat_history),
                len(truncated_history),
            )

        # ── 5. Componer el prompt del usuario ──
        partes: list[str] = []

        if rag_text:
            partes.append(rag_text)

        if truncated_history:
            history_lines = ["## Historial de Conversación\n"]
            for msg in truncated_history:
                role = msg.get("role", "user")
                content = msg.get("content", "")
                if role == "user":
                    history_lines.append(f"**Docente:** {content}")
                elif role == "assistant":
                    history_lines.append(f"**Kantan:** {content}")
                elif role == "system":
                    history_lines.append(f"**Sistema:** {content}")
            partes.append("\n".join(history_lines))

        partes.append(user_msg_text)

        user_prompt = "\n\n".join(partes)

        # ── Logging de debug ──
        total_tokens = system_tokens + self.count_tokens(user_prompt)
        logger.debug(
            "Prompt construido: %d tokens totales (sistema=%d, usuario=%d, "
            "rag=%s, historial=%d msgs)",
            total_tokens,
            system_tokens,
            self.count_tokens(user_prompt),
            "sí" if rag_text else "no",
            len(truncated_history),
        )

        return system_prompt, user_prompt
