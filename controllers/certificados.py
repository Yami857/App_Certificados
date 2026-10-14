import io
import re
import zipfile
from flask import (
    Blueprint,
    abort,
    flash,
    redirect,
    render_template,
    request,
    send_file,
    url_for,
)
import jinja2

from models.certificados import (
    obtener_certificado_individual,
    procesar_datos_completos,
)
from services.carga_excel import (
    procesar_excel_estudiantes,
    procesar_excel_evaluaciones,
)
from services.generador_pdf import generar_pdf_certificado

bp = Blueprint("certificados", __name__)


def _limpiar_nombre_archivo(texto: str) -> str:
    """Convierte texto en un nombre seguro para archivos."""
    cadena = str(texto).strip()
    cadena = re.sub(r"[^\w\s-]", "", cadena)
    return re.sub(r"[-\s]+", "_", cadena)


@bp.route("/")
def tablero():
    """Ruta principal: muestra el tablero con métricas, tabla de estudiantes e inconsistencias."""
    datos = procesar_datos_completos()
    try:
        return render_template(
            "index.html",
            resumen=datos["resumen"],
            estudiantes=datos["estudiantes_clasificados"],
            inconsistencias=datos["inconsistencias"],
            certificables=datos["certificables"],
        )
    except jinja2.exceptions.TemplateNotFound:
        # Fallback informativo mientras disenador-vistas genera la plantilla en views/
        html_fallback = f"""
        <!DOCTYPE html>
        <html lang="es">
        <head>
            <meta charset="UTF-8">
            <title>Tablero - App de Certificados</title>
            <style>
                body {{ font-family: sans-serif; margin: 30px; background-color: #f7f9fc; color: #14213D; }}
                .card {{ background: white; padding: 20px; border-radius: 8px; margin-bottom: 20px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
                .btn {{ background-color: #B8923D; color: white; padding: 8px 16px; text-decoration: none; border-radius: 4px; font-weight: bold; }}
            </style>
        </head>
        <body>
            <h1>App de Certificados de la Academia</h1>
            <div class="card">
                <h2>Cifras Oficiales de Control</h2>
                <p><strong>Aprobación:</strong> {datos['resumen']['aprobacion']}</p>
                <p><strong>Participación:</strong> {datos['resumen']['participacion']}</p>
                <p><strong>Sin certificado:</strong> {datos['resumen']['sin_certificado']}</p>
                <p><strong>Inconsistencias:</strong> {datos['resumen']['inconsistencias']}</p>
                <p><strong>Total Certificables:</strong> {datos['resumen']['total_certificables']}</p>
                <br>
                <a class="btn" href="/descargar-todos">Descargar todos los certificados (.zip)</a>
            </div>
            <p><em>(Vista pendiente de diseño en views/index.html por disenador-vistas)</em></p>
        </body>
        </html>
        """
        return html_fallback, 200, {"Content-Type": "text/html; charset=utf-8"}


@bp.route("/cargar", methods=["GET", "POST"])
def cargar():
    """Ruta del formulario para subir los dos archivos Excel."""
    if request.method == "POST":
        archivo_estudiantes = request.files.get("archivo_estudiantes")
        archivo_evaluaciones = request.files.get("archivo_evaluaciones")

        if not archivo_estudiantes or not archivo_evaluaciones:
            flash("Debe seleccionar ambos archivos Excel para continuar.", "danger")
            return redirect(url_for("certificados.cargar"))

        try:
            procesar_excel_estudiantes(archivo_estudiantes)
            procesar_excel_evaluaciones(archivo_evaluaciones)
            flash("Archivos procesados y cargados exitosamente.", "success")
            return redirect(url_for("certificados.tablero"))
        except Exception as e:
            flash(f"Error procesando los archivos: {e}", "danger")
            return redirect(url_for("certificados.cargar"))

    try:
        return render_template("cargar.html")
    except jinja2.exceptions.TemplateNotFound:
        html_fallback = """
        <!DOCTYPE html>
        <html lang="es">
        <head><meta charset="UTF-8"><title>Cargar Excel</title></head>
        <body style="font-family: sans-serif; margin: 30px;">
            <h2>Carga de Archivos Excel</h2>
            <form method="POST" enctype="multipart/form-data">
                <p><label>Maestro de Estudiantes: <input type="file" name="archivo_estudiantes" required></label></p>
                <p><label>Registro de Evaluaciones: <input type="file" name="archivo_evaluaciones" required></label></p>
                <button type="submit">Cargar Archivos</button>
            </form>
        </body>
        </html>
        """
        return html_fallback, 200, {"Content-Type": "text/html; charset=utf-8"}


@bp.route("/certificado/<identificacion>/<programa>")
def descargar_certificado(identificacion: str, programa: str):
    """Genera y descarga el PDF del certificado individual para un estudiante elegible.

    No genera certificado para registros con 'Sin certificado' ni con inconsistencias.
    """
    estudiante = obtener_certificado_individual(identificacion, programa)
    if not estudiante:
        abort(
            404,
            description="No se puede generar certificado: el estudiante no cumple los requisitos académicos o presenta inconsistencias.",
        )

    pdf_bytes = generar_pdf_certificado(estudiante)
    slug_prog = _limpiar_nombre_archivo(estudiante["programa"])
    nombre_archivo = f"Certificado_{estudiante['identificacion']}_{slug_prog}.pdf"

    return send_file(
        io.BytesIO(pdf_bytes),
        mimetype="application/pdf",
        as_attachment=False,
        download_name=nombre_archivo,
    )


@bp.route("/descargar-todos")
def descargar_todos():
    """Genera un archivo .zip en memoria con todos los certificados PDF de estudiantes elegibles.

    Solo incluye aquellos con tipo 'Aprobación' o 'Participación'.
    """
    datos = procesar_datos_completos()
    certificables = datos.get("certificables", [])

    if not certificables:
        abort(404, description="No hay certificados disponibles para descargar.")

    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, mode="w", compression=zipfile.ZIP_DEFLATED) as zip_file:
        for cert in certificables:
            pdf_bytes = generar_pdf_certificado(cert)
            slug_prog = _limpiar_nombre_archivo(cert["programa"])
            nombre_archivo = f"Certificado_{cert['identificacion']}_{slug_prog}.pdf"
            zip_file.writestr(nombre_archivo, pdf_bytes)

    zip_buffer.seek(0)
    return send_file(
        zip_buffer,
        mimetype="application/zip",
        as_attachment=True,
        download_name="Certificados_Academia.zip",
    )
