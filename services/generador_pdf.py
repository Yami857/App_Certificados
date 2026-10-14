from typing import Any, Dict
from fpdf import FPDF

# Colores institucionales de la Academia
COLOR_AZUL_MARINO = (20, 33, 61)   # #14213D
COLOR_DORADO = (184, 146, 61)      # #B8923D
COLOR_GRIS_OSCURO = (50, 50, 50)
COLOR_GRIS_CLARO = (235, 235, 235)


class CertificadoPDF(FPDF):
    """Clase personalizada de FPDF para dibujar el marco y diseño del certificado."""

    def dibujar_marco_decorativo(self):
        # Marco exterior en dorado
        self.set_draw_color(*COLOR_DORADO)
        self.set_line_width(1.5)
        self.rect(8, 8, 281, 194)

        # Marco interior fino en azul marino
        self.set_draw_color(*COLOR_AZUL_MARINO)
        self.set_line_width(0.5)
        self.rect(12, 12, 273, 186)

        # Detalles en las 4 esquinas interiores
        self.set_draw_color(*COLOR_DORADO)
        self.set_line_width(0.8)
        # Esquina superior izquierda
        self.line(14, 17, 24, 17)
        self.line(17, 14, 17, 24)
        # Esquina superior derecha
        self.line(273, 17, 283, 17)
        self.line(280, 14, 280, 24)
        # Esquina inferior izquierda
        self.line(14, 191, 24, 191)
        self.line(17, 184, 17, 194)
        # Esquina inferior derecha
        self.line(273, 191, 283, 191)
        self.line(280, 184, 280, 194)


def generar_pdf_certificado(datos_estudiante: Dict[str, Any]) -> bytes:
    """Genera un certificado en PDF en formato A4 horizontal con fpdf2.

    Requiere que datos_estudiante incluya:
    - 'nombre_completo'
    - 'identificacion'
    - 'programa'
    - 'cohorte'
    - 'promedio'
    - 'asistencia'
    - 'tipo_certificado' ("Certificado de Aprobación" o "Certificado de Participación")
    """
    pdf = CertificadoPDF(orientation="landscape", unit="mm", format="A4")
    pdf.set_auto_page_break(auto=False, margin=0)
    pdf.add_page()
    pdf.dibujar_marco_decorativo()

    # 1. Encabezado institucional
    pdf.set_y(20)
    pdf.set_font("Helvetica", "B", 13)
    pdf.set_text_color(*COLOR_AZUL_MARINO)
    pdf.cell(0, 7, "ACADEMIA DE FORMACIÓN Y DESARROLLO", align="C", new_x="LMARGIN", new_y="NEXT")

    pdf.set_font("Helvetica", "", 9)
    pdf.set_text_color(*COLOR_DORADO)
    pdf.cell(0, 5, "SISTEMA OFICIAL DE EMISIÓN DE CERTIFICACIONES", align="C", new_x="LMARGIN", new_y="NEXT")

    # Línea divisoria superior
    pdf.set_draw_color(*COLOR_DORADO)
    pdf.set_line_width(0.4)
    pdf.line(70, 34, 227, 34)

    # 2. Título del Certificado según el tipo
    tipo_titulo = datos_estudiante.get("tipo_certificado") or "Certificado de Aprobación"
    pdf.set_y(40)
    pdf.set_font("Helvetica", "B", 24)
    pdf.set_text_color(*COLOR_AZUL_MARINO)
    pdf.cell(0, 12, tipo_titulo, align="C", new_x="LMARGIN", new_y="NEXT")

    # 3. Texto de presentación
    pdf.set_y(54)
    pdf.set_font("Helvetica", "I", 12)
    pdf.set_text_color(*COLOR_GRIS_OSCURO)
    pdf.cell(0, 8, "Hace constar con orgullo y reconocimiento que:", align="C", new_x="LMARGIN", new_y="NEXT")

    # 4. Nombre del estudiante
    nombre = str(datos_estudiante.get("nombre_completo") or "Estudiante").strip()
    pdf.set_y(65)
    pdf.set_font("Helvetica", "B", 22)
    pdf.set_text_color(*COLOR_DORADO)
    pdf.cell(0, 11, nombre, align="C", new_x="LMARGIN", new_y="NEXT")

    # Identificación
    identificacion = str(datos_estudiante.get("identificacion") or "").strip()
    pdf.set_font("Helvetica", "", 11)
    pdf.set_text_color(*COLOR_GRIS_OSCURO)
    pdf.cell(0, 6, f"Identificación: {identificacion}", align="C", new_x="LMARGIN", new_y="NEXT")

    # 5. Programa académico y cohorte
    pdf.set_y(86)
    pdf.set_font("Helvetica", "", 12)
    pdf.set_text_color(*COLOR_GRIS_OSCURO)
    pdf.cell(0, 7, "Ha culminado satisfactoriamente los módulos del programa:", align="C", new_x="LMARGIN", new_y="NEXT")

    programa = str(datos_estudiante.get("programa") or "").strip()
    pdf.set_font("Helvetica", "B", 16)
    pdf.set_text_color(*COLOR_AZUL_MARINO)
    pdf.cell(0, 9, programa, align="C", new_x="LMARGIN", new_y="NEXT")

    cohorte = str(datos_estudiante.get("cohorte") or "").strip()
    if cohorte:
        pdf.set_font("Helvetica", "I", 11)
        pdf.set_text_color(*COLOR_GRIS_OSCURO)
        pdf.cell(0, 6, f"Cohorte: {cohorte}", align="C", new_x="LMARGIN", new_y="NEXT")

    # 6. Recuadro de Calificaciones (Promedio y Asistencia)
    promedio = datos_estudiante.get("promedio", 0.0)
    asistencia = datos_estudiante.get("asistencia", 0.0)

    pdf.set_y(118)
    # Fondo del recuadro de desempeño
    pdf.set_fill_color(248, 246, 240)
    pdf.set_draw_color(*COLOR_DORADO)
    pdf.set_line_width(0.4)
    recuadro_w = 160
    recuadro_x = (297 - recuadro_w) / 2
    pdf.rect(recuadro_x, 118, recuadro_w, 20, style="FD")

    pdf.set_y(123)
    pdf.set_font("Helvetica", "B", 12)
    pdf.set_text_color(*COLOR_AZUL_MARINO)
    texto_metricas = f"Promedio Final: {promedio:.2f} / 100        |        Asistencia: {asistencia:.2f}%"
    pdf.cell(0, 10, texto_metricas, align="C", new_x="LMARGIN", new_y="NEXT")

    # 7. Firmas de la Academia
    pdf.set_y(155)
    pdf.set_draw_color(*COLOR_AZUL_MARINO)
    pdf.set_line_width(0.5)

    # Línea de firma 1
    pdf.line(50, 165, 115, 165)
    # Línea de firma 2
    pdf.line(182, 165, 247, 165)

    pdf.set_y(168)
    pdf.set_font("Helvetica", "B", 10)
    pdf.set_text_color(*COLOR_AZUL_MARINO)

    # Cargo firma 1
    pdf.set_x(40)
    pdf.cell(85, 5, "Dirección Académica", align="C")

    # Cargo firma 2
    pdf.set_x(172)
    pdf.cell(85, 5, "Coordinación de Programa", align="C", new_x="LMARGIN", new_y="NEXT")

    pdf.set_font("Helvetica", "", 8)
    pdf.set_text_color(*COLOR_GRIS_OSCURO)
    pdf.set_x(40)
    pdf.cell(85, 4, "Academia de Formación", align="C")
    pdf.set_x(172)
    pdf.cell(85, 4, "Acreditación y Registros", align="C", new_x="LMARGIN", new_y="NEXT")

    # 8. Pie de página con folio y validez
    pdf.set_y(186)
    pdf.set_font("Helvetica", "I", 8)
    pdf.set_text_color(130, 130, 130)
    pdf.cell(
        0,
        5,
        f"Certificado emitido electrónicamente. Verificación de autenticidad: ID-{identificacion}",
        align="C",
    )

    return bytes(pdf.output())
