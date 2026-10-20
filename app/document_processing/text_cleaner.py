"""Limpieza y normalización de texto extraído de documentos."""

import re
import unicodedata


def clean_and_normalize(text: str) -> str:
    """Limpia y normaliza el texto extraído de un documento.

    Realiza las siguientes transformaciones:
    - Normalización Unicode (NFC)
    - Eliminación de caracteres de control (excepto newlines y tabs)
    - Normalización de espacios en blanco horizontales
    - Colapso de múltiples líneas vacías en doble salto de línea
    - Eliminación de espacios al inicio y final de cada línea
    - Strip global del texto resultante

    Args:
        text: Texto crudo a limpiar.

    Returns:
        Texto limpio y normalizado.
    """
    if not text or not text.strip():
        return ""

    # Normalizar Unicode a forma canónica compuesta (NFC)
    text = unicodedata.normalize("NFC", text)

    # Eliminar caracteres de control excepto \n, \r, \t
    text = re.sub(r"[^\S\n\r\t]", " ", text)  # espacios especiales Unicode → espacio normal
    text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]", "", text)

    # Normalizar retornos de carro (Windows \r\n → \n)
    text = text.replace("\r\n", "\n").replace("\r", "\n")

    # Reemplazar tabs por espacios
    text = text.replace("\t", "    ")

    # Eliminar espacios múltiples horizontales (sin tocar saltos de línea)
    text = re.sub(r"[^\S\n]+", " ", text)

    # Eliminar espacios al inicio y final de cada línea
    text = re.sub(r"^ +| +$", "", text, flags=re.MULTILINE)

    # Colapsar 3 o más saltos de línea consecutivos en exactamente 2
    text = re.sub(r"\n{3,}", "\n\n", text)

    # Strip global
    text = text.strip()

    return text
