"""Generador de documentos Word (.docx) estructurados para Planes Diarios."""

import io
from datetime import datetime
from docx import Document
from docx.enum.table import WD_ALIGN_VERTICAL, WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Inches, Pt

from app.export.styles import (
    COLOR_PRIMARY,
    COLOR_SECONDARY,
    COLOR_TEXT,
    FONT_BODY,
    FONT_SIZE_BODY,
    FONT_SIZE_HEADING,
    FONT_SIZE_TITLE,
    FONT_TITLE,
    HEX_ALT_ROW_BG,
    HEX_HEADER_BG,
    HEX_SECTION_BG,
    HEX_WHITE,
    MARGIN_BOTTOM,
    MARGIN_LEFT,
    MARGIN_RIGHT,
    MARGIN_TOP,
    set_cell_margins,
    set_cell_shading,
)
from app.schemas.plan import PlanDiario


class PlanDocxBuilder:
    """Construye un documento .docx formateado a partir de un objeto PlanDiario."""

    def __init__(self):
        self.doc = Document()
        self._setup_page()

    def _setup_page(self):
        """Configura márgenes y fuentes predeterminadas."""
        for section in self.doc.sections:
            section.top_margin = MARGIN_TOP
            section.bottom_margin = MARGIN_BOTTOM
            section.left_margin = MARGIN_LEFT
            section.right_margin = MARGIN_RIGHT

        # Ajuste estilo Normal
        style = self.doc.styles["Normal"]
        font = style.font
        font.name = FONT_BODY
        font.size = FONT_SIZE_BODY
        font.color.rgb = COLOR_TEXT

    def _add_section_header(self, title: str):
        """Agrega un encabezado de sección con franja de color."""
        p = self.doc.add_paragraph()
        p.paragraph_format.space_before = Pt(14)
        p.paragraph_format.space_after = Pt(4)
        p.paragraph_format.keep_with_next = True

        run = p.add_run(f"■  {title.upper()}")
        run.bold = True
        run.font.name = FONT_TITLE
        run.font.size = FONT_SIZE_HEADING
        run.font.color.rgb = COLOR_PRIMARY

    def _add_title_block(self, datos):
        """Crea la cabecera institucional principal."""
        title_p = self.doc.add_paragraph()
        title_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        title_p.paragraph_format.space_after = Pt(2)
        title_run = title_p.add_run("PLAN DIARIO DE CLASE")
        title_run.bold = True
        title_run.font.name = FONT_TITLE
        title_run.font.size = FONT_SIZE_TITLE
        title_run.font.color.rgb = COLOR_PRIMARY

        sub_p = self.doc.add_paragraph()
        sub_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        sub_p.paragraph_format.space_after = Pt(12)
        inst_text = datos.institucion or "Planificación Docente"
        sub_run = sub_p.add_run(f"{inst_text} — Proyecto Keyoku")
        sub_run.font.size = Pt(10)
        sub_run.font.color.rgb = COLOR_SECONDARY

        # Tabla de Datos Generales
        table = self.doc.add_table(rows=3, cols=2)
        table.alignment = WD_TABLE_ALIGNMENT.CENTER
        table.autofit = False

        data = [
            ("Materia / Asignatura:", datos.materia, "Grado / Nivel:", datos.grado),
            ("Docente:", datos.docente or "No especificado", "Fecha:", str(datos.fecha)),
            ("Duración estimada:", f"{datos.duracion_minutos} minutos", "Ciclo Lectivo:", str(datetime.now().year)),
        ]

        for i, row in enumerate(table.rows):
            left_label, left_val, right_label, right_val = data[i]
            # Columna izquierda
            c1 = row.cells[0]
            p1 = c1.paragraphs[0]
            p1.paragraph_format.space_after = Pt(2)
            r1 = p1.add_run(f"{left_label} ")
            r1.bold = True
            r1.font.size = Pt(9.5)
            r2 = p1.add_run(left_val)
            r2.font.size = Pt(9.5)

            # Columna derecha
            c2 = row.cells[1]
            p2 = c2.paragraphs[0]
            p2.paragraph_format.space_after = Pt(2)
            r3 = p2.add_run(f"{right_label} ")
            r3.bold = True
            r3.font.size = Pt(9.5)
            r4 = p2.add_run(right_val)
            r4.font.size = Pt(9.5)

            set_cell_shading(c1, HEX_ALT_ROW_BG if i % 2 == 0 else HEX_WHITE)
            set_cell_shading(c2, HEX_ALT_ROW_BG if i % 2 == 0 else HEX_WHITE)
            set_cell_margins(c1, top=100, bottom=100, left=150, right=150)
            set_cell_margins(c2, top=100, bottom=100, left=150, right=150)

    def _add_objetivo(self, objetivo: str):
        """Agrega el objetivo pedagógico de la clase."""
        self._add_section_header("1. Objetivo de la Clase")
        p = self.doc.add_paragraph()
        p.paragraph_format.space_after = Pt(6)
        run = p.add_run(objetivo)
        run.italic = True

    def _add_contenidos(self, contenidos: list[str]):
        """Agrega los temas o contenidos conceptuales/procedimentales."""
        self._add_section_header("2. Contenidos y Saberes")
        for item in contenidos:
            p = self.doc.add_paragraph(style="List Bullet")
            p.paragraph_format.space_after = Pt(2)
            p.add_run(item)

    def _add_secuencia_didactica(self, secuencia):
        """Genera la tabla estructurada de Inicio, Desarrollo y Cierre."""
        self._add_section_header("3. Secuencia Didáctica")

        table = self.doc.add_table(rows=4, cols=3)
        table.alignment = WD_TABLE_ALIGNMENT.CENTER
        table.autofit = False

        # Encabezados de tabla
        headers = ["Momento de la Clase", "Duración", "Actividades y Estrategias"]
        for j, text in enumerate(headers):
            cell = table.rows[0].cells[j]
            p = cell.paragraphs[0]
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            p.paragraph_format.space_after = Pt(4)
            run = p.add_run(text)
            run.bold = True
            run.font.color.rgb = COLOR_PRIMARY
            set_cell_shading(cell, HEX_HEADER_BG)
            set_cell_margins(cell, top=120, bottom=120, left=140, right=140)

        etapas = [
            ("Inicio (Apertura)", secuencia.inicio),
            ("Desarrollo (Construcción)", secuencia.desarrollo),
            ("Cierre (Evaluación/Síntesis)", secuencia.cierre),
        ]

        for i, (nombre, sec) in enumerate(etapas, start=1):
            row = table.rows[i]

            # Momento
            c0 = row.cells[0]
            p0 = c0.paragraphs[0]
            p0.alignment = WD_ALIGN_PARAGRAPH.LEFT
            r0 = p0.add_run(nombre)
            r0.bold = True

            # Duración
            c1 = row.cells[1]
            p1 = c1.paragraphs[0]
            p1.alignment = WD_ALIGN_PARAGRAPH.CENTER
            p1.add_run(f"{sec.duracion_minutos} min")

            # Descripción y actividades
            c2 = row.cells[2]
            p2 = c2.paragraphs[0]
            p2.paragraph_format.space_after = Pt(3)
            p2.add_run(sec.descripcion)

            if sec.actividades:
                for act in sec.actividades:
                    bullet_p = c2.add_paragraph(style="List Bullet")
                    bullet_p.paragraph_format.space_after = Pt(2)
                    bullet_p.add_run(act)

            for cell in (c0, c1, c2):
                set_cell_margins(cell, top=100, bottom=100, left=120, right=120)
                if i % 2 == 1:
                    set_cell_shading(cell, HEX_ALT_ROW_BG)

    def _add_recursos_y_evaluacion(self, recursos: list[str], evaluacion):
        """Agrega secciones finales de recursos y evaluación."""
        self._add_section_header("4. Recursos y Materiales Didácticos")
        for rec in recursos:
            p = self.doc.add_paragraph(style="List Bullet")
            p.paragraph_format.space_after = Pt(2)
            p.add_run(rec)

        self._add_section_header("5. Evaluación")
        p = self.doc.add_paragraph()
        p.paragraph_format.space_after = Pt(3)
        r_tipo = p.add_run(f"Tipo de evaluación: {evaluacion.tipo}\n")
        r_tipo.bold = True
        p.add_run(evaluacion.descripcion)

        if evaluacion.criterios:
            p_crit = self.doc.add_paragraph()
            p_crit.paragraph_format.space_before = Pt(4)
            p_crit.paragraph_format.space_after = Pt(2)
            r_crit = p_crit.add_run("Criterios de logro:")
            r_crit.bold = True
            for c in evaluacion.criterios:
                p_item = self.doc.add_paragraph(style="List Bullet")
                p_item.paragraph_format.space_after = Pt(2)
                p_item.add_run(c)

    def build(self, plan: PlanDiario) -> io.BytesIO:
        """Compone todas las secciones y retorna el archivo .docx en memoria."""
        self._add_title_block(plan.datos_generales)
        self._add_objetivo(plan.objetivo)
        self._add_contenidos(plan.contenidos)
        self._add_secuencia_didactica(plan.secuencia_didactica)
        self._add_recursos_y_evaluacion(plan.recursos, plan.evaluacion)

        buffer = io.BytesIO()
        self.doc.save(buffer)
        buffer.seek(0)
        return buffer
