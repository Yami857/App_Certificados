import io
import os
import re
from pathlib import Path

# ---------------------------------------------------------------------------
# Credenciales SOLO para las pruebas.
# Se definen ANTES de importar app para que la app no dependa del .env real
# de la máquina. python-dotenv no pisa variables que ya existen.
# ---------------------------------------------------------------------------
os.environ["ADMIN_CORREO"] = "admin@pruebas.local"
os.environ["ADMIN_CLAVE"] = "ClaveAdminPruebas123"
os.environ["USUARIO_CORREO"] = "usuario@pruebas.local"
os.environ["USUARIO_CLAVE"] = "ClaveUsuarioPruebas123"
os.environ["SECRET_KEY"] = "clave-secreta-solo-para-pruebas"

import pandas as pd  # noqa: E402
import pytest  # noqa: E402

from app import app  # noqa: E402

BASE = Path(__file__).resolve().parent.parent
RUTA_ESTUDIANTES = BASE / "Insumos" / "Maestro_Estudiantes.xlsx"
RUTA_EVALUACIONES = BASE / "Insumos" / "Registro_Evaluaciones.xlsx"

ADMIN_CORREO = os.environ["ADMIN_CORREO"]
ADMIN_CLAVE = os.environ["ADMIN_CLAVE"]


@pytest.fixture()
def cliente():
    """Entrega un "navegador falso" nuevo para cada prueba (sin sesión previa)."""
    app.config.update(TESTING=True)
    with app.test_client() as cliente_flask:
        yield cliente_flask


def iniciar_sesion(cliente, correo: str, clave: str):
    """Simula escribir correo y contraseña en /login y pulsar "Entrar"."""
    return cliente.post("/login", data={"correo": correo, "clave": clave})


def test_sin_sesion_redirige_a_login(cliente):
    """Simula abrir la página principal sin haber entrado: debe mandar a /login."""
    respuesta = cliente.get("/")

    assert respuesta.status_code == 302
    assert "/login" in respuesta.headers["Location"]


def test_clave_incorrecta_no_entra(cliente):
    """Simula entrar con una contraseña equivocada: se queda en el login y ve el error."""
    respuesta = cliente.post(
        "/login",
        data={"correo": ADMIN_CORREO, "clave": "esta-clave-no-es"},
    )
    html = respuesta.get_data(as_text=True)

    assert respuesta.status_code == 200
    assert "Correo o contraseña incorrectos." in html
    assert "Acceso restringido" in html  # sigue en la pantalla de entrada


def test_usuario_no_puede_cargar(cliente):
    """Simula entrar como rol "usuario" y pedir /cargar: debe recibir 403."""
    iniciar_sesion(
        cliente,
        os.environ["USUARIO_CORREO"],
        os.environ["USUARIO_CLAVE"],
    )

    respuesta = cliente.get("/cargar")
    html = respuesta.get_data(as_text=True)

    assert respuesta.status_code == 403
    assert "solo para administradores" in html


def test_excel_modificado_cambia_contadores(cliente):
    """Simula que un admin sube un Excel con las notas de Camila en 40.

    Camila (101230456) tenía promedio 91.25 y aprobaba. Con notas en 40 su
    promedio baja de 70, así que pasa de Aprobación a Participación:
    18 aprobación, 4 participación y 1 sin certificado.
    """
    iniciar_sesion(cliente, ADMIN_CORREO, ADMIN_CLAVE)

    # 1. Construir el Excel modificado EN MEMORIA (el archivo original no se toca)
    df_evaluaciones = pd.read_excel(
        RUTA_EVALUACIONES,
        sheet_name="Evaluaciones",
        dtype={"Identificacion": str},
    )
    es_camila = df_evaluaciones["Identificacion"].astype(str).str.strip() == "101230456"
    df_evaluaciones.loc[es_camila, "Nota"] = 40

    buffer_evaluaciones = io.BytesIO()
    df_evaluaciones.to_excel(buffer_evaluaciones, index=False, sheet_name="Evaluaciones")
    buffer_evaluaciones.seek(0)

    # 2. Subir el maestro original y el registro modificado, como haría el panel
    buffer_estudiantes = io.BytesIO(RUTA_ESTUDIANTES.read_bytes())
    respuesta = cliente.post(
        "/cargar",
        data={
            "accion": "ver",
            "archivo_estudiantes": (buffer_estudiantes, "Maestro_Estudiantes.xlsx"),
            "archivo_evaluaciones": (buffer_evaluaciones, "Registro_Evaluaciones.xlsx"),
        },
        content_type="multipart/form-data",
    )
    html = respuesta.get_data(as_text=True)

    # 3. Leer las tarjetas del tablero en el mismo orden en que se muestran
    valores = re.findall(r'<span class="metric-value">(\d+)</span>', html)

    assert respuesta.status_code == 200
    assert "Estás viendo resultados de los archivos" in html
    # Total certificables, Aprobación, Participación, Sin certificado, Inconsistencias
    assert valores == ["22", "18", "4", "1", "3"]
