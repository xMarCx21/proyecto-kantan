"""Generador de documentos Word (.docx) con formato oficial MEC Paraguay y Ficha de Clase."""

from __future__ import annotations

import io
from datetime import datetime
from typing import Any
from docx import Document
from docx.enum.table import WD_ALIGN_VERTICAL, WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Cm, Inches, Pt, RGBColor

from app.export.styles import (
    COLOR_MUTED,
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
    set_cell_margins,
    set_cell_shading,
)
from app.schemas.plan import PlanDiario


class PlanDocxBuilder:
    """Construye un documento .docx oficial de Plan Diario y Ficha de Clase (MEC Paraguay)."""

    def __init__(self, doc: Document | None = None):
        if doc is not None:
            self.doc = doc
            self.custom_template = True
        else:
            self.doc = Document()
            self.custom_template = False
            self._setup_page()

    def _setup_page(self):
        """Configura márgenes y fuentes predeterminadas optimizadas para la tabla oficial."""
        for section in self.doc.sections:
            section.top_margin = Cm(1.5)
            section.bottom_margin = Cm(1.5)
            section.left_margin = Cm(1.5)
            section.right_margin = Cm(1.5)

        # Ajuste estilo Normal
        style = self.doc.styles["Normal"]
        font = style.font
        font.name = FONT_BODY
        font.size = Pt(10)
        font.color.rgb = COLOR_TEXT

    def _add_curricular_header(self, plan: PlanDiario):
        """Agrega el encabezado de identificación curricular oficial."""
        dg = plan.datos_generales
        mes_val = dg.mes or "Setiembre"
        ano_val = dg.ano or 2026

        # Fila superior de datos curriculares
        p_info = self.doc.add_paragraph()
        p_info.paragraph_format.space_before = Pt(0)
        p_info.paragraph_format.space_after = Pt(4)

        r_area = p_info.add_run("Área: ")
        r_area.bold = True
        r_area.font.color.rgb = COLOR_PRIMARY
        p_info.add_run(f"{dg.materia}\t")

        r_grado = p_info.add_run("Grado: ")
        r_grado.bold = True
        r_grado.font.color.rgb = COLOR_PRIMARY
        p_info.add_run(f"{dg.grado}\t")

        r_mes = p_info.add_run("Mes: ")
        r_mes.bold = True
        r_mes.font.color.rgb = COLOR_PRIMARY
        p_info.add_run(f"{mes_val}\t")

        r_ano = p_info.add_run("Año: ")
        r_ano.bold = True
        r_ano.font.color.rgb = COLOR_PRIMARY
        p_info.add_run(f"{ano_val}")

        # Institución y Docente
        p_sub = self.doc.add_paragraph()
        p_sub.paragraph_format.space_after = Pt(8)
        p_sub.add_run("Institución: ").bold = True
        p_sub.add_run(f"{dg.institucion or 'Institución Educativa'}\t\t")
        p_sub.add_run("Docente: ").bold = True
        p_sub.add_run(f"{dg.docente or 'No especificado'}")

    def _add_mec_curricular_table(self, plan: PlanDiario):
        """Genera la Tabla Curricular Oficial del MEC de 8 columnas."""
        dg = plan.datos_generales

        # Crear tabla de 8 columnas
        table = self.doc.add_table(rows=2, cols=8)
        table.alignment = WD_TABLE_ALIGNMENT.CENTER
        table.autofit = False

        headers = [
            "Fecha",
            "Tiempo",
            "Temas",
            "Unidad temática",
            "Capacidades",
            "Indicadores",
            "Momentos didácticos",
            "Instrumento evaluativo",
        ]

        # Anchos en pulgadas (total = ~7.4 in)
        col_widths = [
            Inches(0.65),  # Fecha
            Inches(0.65),  # Tiempo
            Inches(1.10),  # Temas
            Inches(1.00),  # Unidad temática
            Inches(1.45),  # Capacidades
            Inches(1.45),  # Indicadores
            Inches(1.10),  # Momentos
            Inches(0.70),  # Instrumento
        ]

        # Configurar cabecera
        header_row = table.rows[0]
        for j, text in enumerate(headers):
            cell = header_row.cells[j]
            cell.width = col_widths[j]
            p = cell.paragraphs[0]
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            p.paragraph_format.space_after = Pt(2)
            run = p.add_run(text)
            run.bold = True
            run.font.name = FONT_TITLE
            run.font.size = Pt(8.5)
            run.font.color.rgb = COLOR_PRIMARY
            set_cell_shading(cell, HEX_HEADER_BG)
            set_cell_margins(cell, top=80, bottom=80, left=90, right=90)

        # Configurar fila de datos
        data_row = table.rows[1]
        for j in range(8):
            data_row.cells[j].width = col_widths[j]
            set_cell_margins(data_row.cells[j], top=80, bottom=80, left=90, right=90)

        # 0. Fecha
        p0 = data_row.cells[0].paragraphs[0]
        p0.alignment = WD_ALIGN_PARAGRAPH.CENTER
        r0 = p0.add_run(str(dg.fecha or datetime.now().strftime("%d/%m/%Y")))
        r0.font.size = Pt(8.5)

        # 1. Tiempo
        p1 = data_row.cells[1].paragraphs[0]
        p1.alignment = WD_ALIGN_PARAGRAPH.CENTER
        r1 = p1.add_run(f"{dg.duracion_minutos} min.")
        r1.font.size = Pt(8.5)

        # 2. Temas
        p2 = data_row.cells[2].paragraphs[0]
        r2 = p2.add_run(plan.tema or dg.materia)
        r2.bold = True
        r2.font.size = Pt(8.5)

        # 3. Unidad temática
        p3 = data_row.cells[3].paragraphs[0]
        r3 = p3.add_run(plan.unidad_tematica or "El número y las operaciones")
        r3.font.size = Pt(8.5)

        # 4. Capacidades
        c4 = data_row.cells[4]
        caps = plan.capacidades or [
            "Comprende el problema enunciado.",
            "Identifica estrategias requeridas para la solución de problemas.",
            "Ejecuta el plan de solución.",
            "Examina la solución obtenida y comunica la respuesta adecuadamente.",
        ]
        for idx, cap in enumerate(caps):
            p = c4.paragraphs[0] if idx == 0 else c4.add_paragraph()
            p.paragraph_format.space_after = Pt(2)
            r = p.add_run(f"• {cap}")
            r.font.size = Pt(8)

        # 5. Indicadores
        c5 = data_row.cells[5]
        inds = plan.indicadores or [
            "Interpreta la información del problema.",
            "Aplica la fórmula o algoritmo correcto.",
            "Opera sin error las operaciones matemáticas.",
            "Comunica la respuesta en forma coherente.",
        ]
        for idx, ind in enumerate(inds):
            p = c5.paragraphs[0] if idx == 0 else c5.add_paragraph()
            p.paragraph_format.space_after = Pt(2)
            r = p.add_run(f"• {ind}")
            r.font.size = Pt(8)

        # 6. Momentos didácticos
        p6 = data_row.cells[6].paragraphs[0]
        momentos_texto = plan.momentos_didacticos_resumen or (
            "Observamos la situación disparadora inicial.\n"
            "Leemos y analizamos información teórica.\n"
            "Deducimos fórmulas en el pizarrón.\n"
            "Resolvemos ejercicios prácticos en el cuaderno."
        )
        r6 = p6.add_run(momentos_texto)
        r6.font.size = Pt(8)

        # 7. Instrumento evaluativo
        p7 = data_row.cells[7].paragraphs[0]
        p7.alignment = WD_ALIGN_PARAGRAPH.CENTER
        r7 = p7.add_run(plan.instrumento_evaluativo or "R.S.A.")
        r7.bold = True
        r7.font.size = Pt(8.5)

        # Espacio posterior a la tabla
        p_spacer = self.doc.add_paragraph()
        p_spacer.paragraph_format.space_before = Pt(8)
        p_spacer.paragraph_format.space_after = Pt(4)

    def _add_worksheet_section(self, plan: PlanDiario):
        """Genera la Ficha de Clase con ejercitario práctico (para el aula)."""
        tema_title = (plan.tema or plan.datos_generales.materia).upper()

        # Banner destacado del tema
        banner_table = self.doc.add_table(rows=1, cols=1)
        banner_table.alignment = WD_TABLE_ALIGNMENT.CENTER
        b_cell = banner_table.rows[0].cells[0]
        b_p = b_cell.paragraphs[0]
        b_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        b_p.paragraph_format.space_after = Pt(3)
        b_run = b_p.add_run(f"■  {tema_title}")
        b_run.bold = True
        b_run.font.name = FONT_TITLE
        b_run.font.size = Pt(13)
        b_run.font.color.rgb = COLOR_PRIMARY
        set_cell_shading(b_cell, HEX_HEADER_BG)
        set_cell_margins(b_cell, top=100, bottom=100, left=150, right=150)

        # 1. Situación Disparadora (Inicio / Motivación)
        p_s1 = self.doc.add_paragraph()
        p_s1.paragraph_format.space_before = Pt(12)
        p_s1.paragraph_format.space_after = Pt(3)
        r_s1 = p_s1.add_run("1. Situación Problemática Inicial (Inicio / Motivación)")
        r_s1.bold = True
        r_s1.font.color.rgb = COLOR_PRIMARY

        sit_table = self.doc.add_table(rows=1, cols=1)
        sit_table.alignment = WD_TABLE_ALIGNMENT.CENTER
        s_cell = sit_table.rows[0].cells[0]
        s_p = s_cell.paragraphs[0]
        s_p.paragraph_format.space_after = Pt(2)
        sit_texto = plan.situacion_disparadora or (
            f"Para iniciar la clase, analizamos una situación de la vida diaria relacionada a {plan.tema or 'los contenidos'}. "
            "Leemos la situación en conjunto, formulamos preguntas disparadoras y registramos ideas previas en el pizarrón."
        )
        r_sit = s_p.add_run(sit_texto)
        r_sit.font.size = Pt(9.5)
        r_sit.italic = True
        set_cell_shading(s_cell, HEX_ALT_ROW_BG)
        set_cell_margins(s_cell, top=100, bottom=100, left=140, right=140)

        # 2. Conceptualización y Fórmulas ("Para saber / Para recordar")
        p_s2 = self.doc.add_paragraph()
        p_s2.paragraph_format.space_before = Pt(10)
        p_s2.paragraph_format.space_after = Pt(3)
        r_s2 = p_s2.add_run("2. Conceptualización y Reglas Clave (\"Para recordar / Para saber\")")
        r_s2.bold = True
        r_s2.font.color.rgb = COLOR_PRIMARY

        concep_table = self.doc.add_table(rows=1, cols=1)
        concep_table.alignment = WD_TABLE_ALIGNMENT.CENTER
        c_cell = concep_table.rows[0].cells[0]
        c_p = c_cell.paragraphs[0]
        c_p.paragraph_format.space_after = Pt(2)
        concep_texto = plan.conceptualizacion or (
            f"Fórmulas y conceptos centrales: Identificamos los elementos y relaciones fundamentales de {plan.tema or 'la lección'}. "
            "Recordamos que para resolver problemas debemos extraer los datos, seleccionar la fórmula adecuada y operar ordenadamente."
        )
        r_con = c_p.add_run(concep_texto)
        r_con.font.size = Pt(9.5)
        set_cell_shading(c_cell, "FCFDFD")
        set_cell_margins(c_cell, top=90, bottom=90, left=130, right=130)

        # 3. Ejercitario Práctico ("Resuelvo los siguientes problemas")
        p_s3 = self.doc.add_paragraph()
        p_s3.paragraph_format.space_before = Pt(12)
        p_s3.paragraph_format.space_after = Pt(4)
        r_s3 = p_s3.add_run("3. Ejercitario Práctico de Clase (\"Resuelvo\")")
        r_s3.bold = True
        r_s3.font.color.rgb = COLOR_PRIMARY

        problemas_list = plan.problemas
        if not problemas_list:
            # Generar problemas por defecto si no vinieron en el objeto
            tema_txt = plan.tema or "matemáticas"
            problemas_list = [
                type("Prob", (), {
                    "numero": 1,
                    "enunciado": f"Se necesita resolver una situación práctica sobre {tema_txt} aplicando los datos conocidos. Analiza y determina la solución.",
                    "datos": "Datos del problema",
                    "formula": "Fórmula aplicable",
                    "solucion": "Desarrollo del cálculo",
                    "respuesta": "Respuesta contextualizada.",
                })(),
                type("Prob", (), {
                    "numero": 2,
                    "enunciado": f"Calcula y fundamenta el procedimiento para determinar el resultado requerido en situaciones de {tema_txt}.",
                    "datos": "Datos identificados",
                    "formula": "Fórmula",
                    "solucion": "Operación",
                    "respuesta": "Resultado final.",
                })()
            ]

        for p_idx, prob in enumerate(problemas_list, start=1):
            p_num = getattr(prob, "numero", p_idx)
            enunciado = getattr(prob, "enunciado", str(prob))

            p_enun = self.doc.add_paragraph()
            p_enun.paragraph_format.space_before = Pt(6)
            p_enun.paragraph_format.space_after = Pt(3)
            p_enun.paragraph_format.keep_with_next = True
            r_num = p_enun.add_run(f"Problema {p_num}: ")
            r_num.bold = True
            r_num.font.color.rgb = COLOR_SECONDARY
            p_enun.add_run(enunciado).font.size = Pt(9.5)

            # Cuadrícula de 3 columnas para Datos | Fórmula / Dibujo | Solución
            grid_tbl = self.doc.add_table(rows=2, cols=3)
            grid_tbl.alignment = WD_TABLE_ALIGNMENT.CENTER
            grid_tbl.autofit = False

            col_w = [Inches(2.2), Inches(2.2), Inches(2.9)]
            headers_grid = ["Datos", "Fórmula / Dibujo", "Solución"]

            # Cabecera de cuadrícula
            for k in range(3):
                c = grid_tbl.rows[0].cells[k]
                c.width = col_w[k]
                p = c.paragraphs[0]
                p.alignment = WD_ALIGN_PARAGRAPH.CENTER
                p.paragraph_format.space_after = Pt(1)
                r = p.add_run(headers_grid[k])
                r.bold = True
                r.font.size = Pt(8.5)
                set_cell_shading(c, HEX_ALT_ROW_BG)
                set_cell_margins(c, top=50, bottom=50, left=80, right=80)

            # Fila de trabajo (con datos sugeridos o espacio para escribir)
            datos_val = getattr(prob, "datos", "")
            form_val = getattr(prob, "formula", "")
            sol_val = getattr(prob, "solucion", "")

            row1 = grid_tbl.rows[1]
            for k, val in enumerate([datos_val, form_val, sol_val]):
                c = row1.cells[k]
                c.width = col_w[k]
                p = c.paragraphs[0]
                p.paragraph_format.space_after = Pt(2)
                if val:
                    r = p.add_run(val)
                    r.font.size = Pt(8.5)
                else:
                    p.add_run("\n\n\n")
                set_cell_margins(c, top=70, bottom=70, left=80, right=80)

            # Línea de respuesta
            resp_val = getattr(prob, "respuesta", "")
            p_resp = self.doc.add_paragraph()
            p_resp.paragraph_format.space_before = Pt(3)
            p_resp.paragraph_format.space_after = Pt(8)
            r_rtitle = p_resp.add_run("Respuesta: ")
            r_rtitle.bold = True
            r_rtitle.font.size = Pt(9)
            if resp_val:
                r_rtext = p_resp.add_run(resp_val)
                r_rtext.font.size = Pt(9)
            else:
                p_resp.add_run("__________________________________________________________________________")

        # Ejercicios de aplicación complementarios si existen
        if plan.ejercicios_aplicacion:
            p_app_title = self.doc.add_paragraph()
            p_app_title.paragraph_format.space_before = Pt(6)
            p_app_title.paragraph_format.space_after = Pt(2)
            r_at = p_app_title.add_run("• Ejercicios complementarios de fijación:")
            r_at.bold = True
            r_at.font.size = Pt(9.5)
            for ej in plan.ejercicios_aplicacion:
                p_ej = self.doc.add_paragraph(style="List Bullet")
                p_ej.paragraph_format.space_after = Pt(2)
                p_ej.add_run(ej).font.size = Pt(9)

        # 4. Tabla de Indicadores de Logro (R.S.A.)
        p_rsa = self.doc.add_paragraph()
        p_rsa.paragraph_format.space_before = Pt(12)
        p_rsa.paragraph_format.space_after = Pt(4)
        p_rsa.paragraph_format.keep_with_next = True
        r_rsa = p_rsa.add_run("4. Indicadores de Logro de la Actividad (Instrumento: R.S.A.)")
        r_rsa.bold = True
        r_rsa.font.color.rgb = COLOR_PRIMARY

        inds = plan.indicadores or [
            "Identifica los datos en situaciones problemáticas.",
            "Determina y aplica las fórmulas o algoritmos correspondientes.",
            "Opera sin error en los cálculos matemáticos.",
            "Comunica la respuesta utilizando la unidad de medida adecuada.",
        ]

        tbl_ind = self.doc.add_table(rows=len(inds) + 1, cols=4)
        tbl_ind.alignment = WD_TABLE_ALIGNMENT.CENTER
        tbl_ind.autofit = False

        ind_col_w = [Inches(0.5), Inches(4.7), Inches(1.1), Inches(1.1)]
        h_ind = ["N°", "Indicadores a Evaluar", "Logrado (L)", "No Logrado (NL)"]

        for k in range(4):
            c = tbl_ind.rows[0].cells[k]
            c.width = ind_col_w[k]
            p = c.paragraphs[0]
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            p.paragraph_format.space_after = Pt(2)
            r = p.add_run(h_ind[k])
            r.bold = True
            r.font.size = Pt(8.5)
            set_cell_shading(c, HEX_HEADER_BG)
            set_cell_margins(c, top=60, bottom=60, left=80, right=80)

        for i, ind_text in enumerate(inds, start=1):
            row = tbl_ind.rows[i]
            # N°
            c0 = row.cells[0]
            c0.width = ind_col_w[0]
            p0 = c0.paragraphs[0]
            p0.alignment = WD_ALIGN_PARAGRAPH.CENTER
            p0.add_run(str(i)).font.size = Pt(8.5)

            # Indicador
            c1 = row.cells[1]
            c1.width = ind_col_w[1]
            p1 = c1.paragraphs[0]
            p1.add_run(ind_text).font.size = Pt(8.5)

            # Casillas L / NL
            for k in [2, 3]:
                c = row.cells[k]
                c.width = ind_col_w[k]
                p = c.paragraphs[0]
                p.alignment = WD_ALIGN_PARAGRAPH.CENTER
                p.add_run("[   ]").font.size = Pt(8.5)

            for cell in (c0, c1, row.cells[2], row.cells[3]):
                set_cell_margins(cell, top=60, bottom=60, left=80, right=80)

        # Firmas institucionales
        p_firma = self.doc.add_paragraph()
        p_firma.paragraph_format.space_before = Pt(24)
        p_firma.paragraph_format.space_after = Pt(2)
        p_firma.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p_firma.add_run("____________________________________            ____________________________________\n")
        r_f1 = p_firma.add_run(f"Prof. {plan.datos_generales.docente or 'Docente'}\t\t\tFirma de Dirección")
        r_f1.font.size = Pt(9)
        r_f1.font.color.rgb = COLOR_MUTED

    def build(self, plan: PlanDiario) -> io.BytesIO:
        """Compone la planificación completa oficial con su ejercitario y retorna el .docx en memoria."""
        if not self.custom_template:
            self._add_curricular_header(plan)
            self._add_mec_curricular_table(plan)
        self._add_worksheet_section(plan)

        buffer = io.BytesIO()
        self.doc.save(buffer)
        buffer.seek(0)
        return buffer
