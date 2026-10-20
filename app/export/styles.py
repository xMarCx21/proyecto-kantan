"""Estilos y utilidades de formateo para documentos Word (.docx)."""

from docx.oxml import parse_xml
from docx.oxml.ns import nsdecls
from docx.shared import Cm, Pt, RGBColor

# ── Fuentes ──
FONT_TITLE = "Arial"
FONT_BODY = "Arial"

# ── Tamaños de Fuente ──
FONT_SIZE_TITLE = Pt(16)
FONT_SIZE_SUBTITLE = Pt(12)
FONT_SIZE_HEADING = Pt(12)
FONT_SIZE_BODY = Pt(10.5)
FONT_SIZE_SMALL = Pt(9)

# ── Paleta de Colores (Azul Educativo Institucional) ──
COLOR_PRIMARY = RGBColor(0x1F, 0x4E, 0x79)       # Azul oscuro encabezados
COLOR_SECONDARY = RGBColor(0x2E, 0x75, 0xB6)     # Azul intermedio
COLOR_TEXT = RGBColor(0x26, 0x26, 0x26)          # Texto principal
COLOR_MUTED = RGBColor(0x59, 0x59, 0x59)         # Texto secundario

# Colores Hexadecimales para sombreado XML
HEX_HEADER_BG = "D6E4F0"     # Azul muy claro para cabeceras de tablas
HEX_SECTION_BG = "1F4E79"    # Azul oscuro de títulos de bloque
HEX_ALT_ROW_BG = "F2F5F9"    # Fila alternativa suave
HEX_WHITE = "FFFFFF"

# ── Márgenes Estándar (A4 / Carta) ──
MARGIN_TOP = Cm(2.0)
MARGIN_BOTTOM = Cm(2.0)
MARGIN_LEFT = Cm(2.5)
MARGIN_RIGHT = Cm(2.5)


def set_cell_shading(cell, hex_color: str):
    """Aplica color de fondo a una celda de tabla en formato hexadecimal."""
    shading_xml = f'<w:shd {nsdecls("w")} w:fill="{hex_color}"/>'
    cell._tc.get_or_add_tcPr().append(parse_xml(shading_xml))


def set_cell_margins(cell, top=120, bottom=120, left=150, right=150):
    """Establece márgenes internos (padding) para una celda de tabla en dxa."""
    tcPr = cell._tc.get_or_add_tcPr()
    tcMar = parse_xml(
        f'<w:tcMar {nsdecls("w")}>'
        f'<w:top w:w="{top}" w:type="dxa"/>'
        f'<w:bottom w:w="{bottom}" w:type="dxa"/>'
        f'<w:left w:w="{left}" w:type="dxa"/>'
        f'<w:right w:w="{right}" w:type="dxa"/>'
        f'</w:tcMar>'
    )
    tcPr.append(tcMar)
