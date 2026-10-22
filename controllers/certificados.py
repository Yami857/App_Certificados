import io
import re
import zipfile
from datetime import date
from pathlib import Path

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

from controllers.auth import requiere_login, solo_admin
from models.certificados import (
    obtener_certificado_individual,
    procesar_datos_completos,
)
from services.generador_excel import generar_excel_resultados
from services.generador_pdf import generar_pdf_certificado

bp = Blueprint("certificados", __name__)

# Límites de los Excel subidos (Vercel rechaza peticiones de más de 4.5 MB).
TAMANO_MAXIMO_ARCHIVO = 4 * 1024 * 1024  # 4 MB por archivo
MIMETYPE_XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


def _limpiar_nombre_archivo(texto: str) -> str:
    """Convierte texto en un nombre seguro para archivos."""
    cadena = str(texto).strip()
    cadena = re.sub(r"[^\w\s-]", "", cadena)
    return re.sub(r"[-\s]+", "_", cadena)


def _contexto_tablero(
    datos: dict,
    origen_datos: str = "Datos de fábrica",
    aviso_datos_subidos: bool = False,
) -> dict:
    """Arma las variables que necesita index.html.

    Sirve tanto para el tablero normal como para mostrar resultados recién
    calculados con archivos subidos.
    """
    return {
        "resumen": datos["resumen"],
        "estudiantes": datos["estudiantes_clasificados"],
        "inconsistencias": datos["inconsistencias"],
        "certificables": datos["certificables"],
        "origen_datos": origen_datos,
        "aviso_datos_subidos": aviso_datos_subidos,
    }


def _leer_archivo_subido(archivo, etiqueta: str):
    """Valida un Excel subido y lo deja en memoria, sin tocar el disco.

    BytesIO es como una caja de cartón con el archivo adentro que vive en la
    memoria RAM de la computadora: se puede abrir y leer, pero no queda nada
    guardado en el disco duro. Por eso sirve en Vercel, donde el disco es de
    solo lectura.

    Devuelve una tupla (nombre, buffer, mensaje_error). Si todo está bien,
    mensaje_error es None.
    """
    if archivo is None or not archivo.filename:
        return None, None, f"Falta el archivo de {etiqueta}."

    # Path(...).name quita cualquier ruta que venga en el nombre (por seguridad).
    nombre = Path(archivo.filename).name

    if not nombre.lower().endswith(".xlsx"):
        return None, None, (
            f"El archivo de {etiqueta} debe ser un Excel .xlsx "
            f"(recibido: {nombre})."
        )

    contenido = archivo.read()

    if not contenido:
        return None, None, f"El archivo de {etiqueta} está vacío."

    if len(contenido) > TAMANO_MAXIMO_ARCHIVO:
        megabytes = len(contenido) / (1024 * 1024)
        return None, None, (
            f"El archivo de {etiqueta} pesa {megabytes:.1f} MB; "
            "el máximo permitido por archivo es 4 MB."
        )

    # Guardamos los bytes del Excel dentro de la "caja" en memoria.
    return nombre, io.BytesIO(contenido), None


@bp.route("/")
@requiere_login
def tablero():
    """Ruta principal: muestra el tablero con métricas, tabla de estudiantes e inconsistencias."""
    datos = procesar_datos_completos()
    try:
        return render_template("index.html", **_contexto_tablero(datos))
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
@requiere_login
@solo_admin
def cargar():
    """Procesa los dos Excel subidos desde el panel de administrador.

    - accion="ver": recalcula y muestra el tablero con esos datos.
    - accion="descargar": devuelve un Excel con los resultados.

    Los archivos se leen EN MEMORIA (io.BytesIO) y no se guardan en ningún
    lado: los resultados viven solo en la respuesta que se muestra o descarga.
    """
    if request.method == "GET":
        # El formulario ahora vive en el tablero, dentro del panel de admin.
        return redirect(url_for("certificados.tablero"))

    accion = request.form.get("accion", "ver")

    # 1. Validar y llevar ambos archivos a memoria
    nombre_estudiantes, buffer_estudiantes, error = _leer_archivo_subido(
        request.files.get("archivo_estudiantes"),
        "estudiantes",
    )
    if error:
        flash(error, "danger")
        return redirect(url_for("certificados.tablero"))

    nombre_evaluaciones, buffer_evaluaciones, error = _leer_archivo_subido(
        request.files.get("archivo_evaluaciones"),
        "evaluaciones",
    )
    if error:
        flash(error, "danger")
        return redirect(url_for("certificados.tablero"))

    # 2. Recalcular con la misma lógica de negocio (R1 a R6)
    try:
        datos = procesar_datos_completos(
            archivo_estudiantes=buffer_estudiantes,
            archivo_evaluaciones=buffer_evaluaciones,
        )
    except Exception as error_lectura:
        # Archivo dañado, hoja/columna faltante, formato raro, etc.
        detalle = str(error_lectura).strip()[:180]
        mensaje = (
            "No pudimos leer los archivos. Verifica que sean Excel .xlsx válidos, "
            "con las hojas 'Estudiantes' y 'Evaluaciones' y sus columnas obligatorias."
        )
        if detalle:
            mensaje = f"{mensaje} Detalle: {detalle}"
        flash(mensaje, "danger")
        return redirect(url_for("certificados.tablero"))

    # 3. Descargar Excel o mostrar los resultados en pantalla
    if accion == "descargar":
        excel_bytes = generar_excel_resultados(datos)
        nombre_descarga = f"Resultados_Academia_{date.today().isoformat()}.xlsx"
        return send_file(
            io.BytesIO(excel_bytes),
            mimetype=MIMETYPE_XLSX,
            as_attachment=True,
            download_name=nombre_descarga,
        )

    origen = f"{nombre_estudiantes} + {nombre_evaluaciones}"
    return render_template(
        "index.html",
        **_contexto_tablero(datos, origen_datos=origen, aviso_datos_subidos=True),
    )


@bp.route("/descargar-excel")
@requiere_login
def descargar_excel():
    """Descarga un Excel con los resultados de los datos de fábrica."""
    datos = procesar_datos_completos()
    excel_bytes = generar_excel_resultados(datos)
    nombre_descarga = f"Resultados_Academia_{date.today().isoformat()}.xlsx"

    return send_file(
        io.BytesIO(excel_bytes),
        mimetype=MIMETYPE_XLSX,
        as_attachment=True,
        download_name=nombre_descarga,
    )


@bp.app_errorhandler(413)
def carga_demasiado_grande(error):
    """Aviso amable cuando la petición completa supera MAX_CONTENT_LENGTH."""
    flash(
        "La carga supera el límite de 4.5 MB permitido. "
        "Sube archivos más livianos e inténtalo de nuevo.",
        "danger",
    )
    return redirect(url_for("certificados.tablero"))


@bp.route("/certificado/<identificacion>/<programa>")
@requiere_login
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
@requiere_login
@solo_admin
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
