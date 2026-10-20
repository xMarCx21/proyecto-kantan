"""División de texto en fragmentos (chunks) con solapamiento."""

import re
import logging

logger = logging.getLogger(__name__)

# Patrones de división ordenados por prioridad (más estructural → menos)
_SPLIT_PATTERNS: list[re.Pattern] = [
    re.compile(r"\n\n+"),   # Doble salto de línea (separador de párrafos)
    re.compile(r"\n"),       # Salto de línea simple
    re.compile(r"(?<=[.!?])\s+"),  # Final de oración
]


def _split_by_priority(text: str, max_size: int) -> list[str]:
    """Divide texto respetando límites naturales según prioridad.

    Intenta dividir primero por párrafos (\\n\\n), luego por líneas (\\n),
    y finalmente por oraciones. Si ningún separador funciona, corta por
    límite duro de caracteres.

    Args:
        text: Texto a dividir.
        max_size: Tamaño máximo de cada fragmento.

    Returns:
        Lista de fragmentos de texto.
    """
    if len(text) <= max_size:
        return [text]

    # Intentar cada patrón de división por prioridad
    for pattern in _SPLIT_PATTERNS:
        segments = pattern.split(text)

        if len(segments) <= 1:
            continue

        # Reconstruir los separadores para preservar la estructura
        separators = pattern.findall(text)

        chunks: list[str] = []
        current = segments[0]

        for i, segment in enumerate(segments[1:]):
            separator = separators[i] if i < len(separators) else ""
            candidate = current + separator + segment

            if len(candidate) <= max_size:
                current = candidate
            else:
                if current.strip():
                    chunks.append(current.strip())
                current = segment

        if current.strip():
            chunks.append(current.strip())

        if chunks:
            # Si algún chunk sigue siendo demasiado grande, subdividirlo
            result: list[str] = []
            for chunk in chunks:
                if len(chunk) > max_size:
                    result.extend(_split_by_priority(chunk, max_size))
                else:
                    result.append(chunk)
            return result

    # Último recurso: corte duro por caracteres intentando respetar palabras
    chunks = []
    start = 0
    while start < len(text):
        end = start + max_size
        if end >= len(text):
            chunk = text[start:].strip()
            if chunk:
                chunks.append(chunk)
            break

        # Buscar el último espacio dentro del rango
        space_pos = text.rfind(" ", start, end)
        if space_pos > start:
            end = space_pos

        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        start = end

    return chunks


def split_into_chunks(
    text: str,
    chunk_size: int = 800,
    overlap: int = 100,
) -> list[dict]:
    """Divide texto en fragmentos solapados para procesamiento RAG.

    Utiliza división consciente de la estructura del texto: primero intenta
    dividir por párrafos, luego por líneas, y finalmente por oraciones.

    Args:
        text: Texto completo a dividir.
        chunk_size: Tamaño máximo en caracteres de cada fragmento.
        overlap: Cantidad de caracteres de solapamiento entre fragmentos consecutivos.

    Returns:
        Lista de diccionarios, cada uno con:
        - content (str): Contenido del fragmento.
        - chunk_index (int): Índice del fragmento (0-based).
        - metadata (dict): Metadatos con char_start y char_end.
    """
    if not text or not text.strip():
        return []

    text = text.strip()

    if chunk_size <= 0:
        raise ValueError("chunk_size debe ser mayor a 0")

    if overlap < 0:
        raise ValueError("overlap debe ser mayor o igual a 0")

    if overlap >= chunk_size:
        raise ValueError("overlap debe ser menor que chunk_size")

    # Dividir el texto en fragmentos base
    raw_chunks = _split_by_priority(text, chunk_size)

    if not raw_chunks:
        return []

    # Aplicar solapamiento entre fragmentos consecutivos
    chunks_con_overlap: list[str] = []

    for i, chunk in enumerate(raw_chunks):
        if i == 0:
            chunks_con_overlap.append(chunk)
            continue

        # Obtener el final del chunk anterior como contexto de solapamiento
        prev_chunk = raw_chunks[i - 1]
        if overlap > 0 and len(prev_chunk) > overlap:
            # Buscar inicio de palabra para el overlap
            overlap_text = prev_chunk[-overlap:]
            space_pos = overlap_text.find(" ")
            if space_pos != -1:
                overlap_text = overlap_text[space_pos + 1:]
            overlap_chunk = overlap_text + " " + chunk
        elif overlap > 0:
            overlap_chunk = prev_chunk + " " + chunk
        else:
            overlap_chunk = chunk

        # Si el chunk con overlap es demasiado largo, usar solo el chunk original
        if len(overlap_chunk) > chunk_size * 1.5:
            chunks_con_overlap.append(chunk)
        else:
            chunks_con_overlap.append(overlap_chunk)

    # Construir resultado con metadatos
    resultado: list[dict] = []
    char_position = 0

    for idx, chunk_content in enumerate(chunks_con_overlap):
        # Calcular posición aproximada en el texto original
        char_start = text.find(chunk_content[:50], max(0, char_position - overlap))
        if char_start == -1:
            char_start = char_position

        char_end = char_start + len(chunk_content)
        char_position = char_start + len(chunk_content) - overlap

        resultado.append({
            "content": chunk_content,
            "chunk_index": idx,
            "metadata": {
                "char_start": char_start,
                "char_end": min(char_end, len(text)),
            },
        })

    logger.info(
        "Texto dividido en %d chunks (chunk_size=%d, overlap=%d)",
        len(resultado),
        chunk_size,
        overlap,
    )

    return resultado
