# App de Certificados — Academia Horizonte (Flask MVC, Python 3.12)

Centro de formación que imparte programas técnicos a empresas; al cerrar cada
cohorte emite un certificado por estudiante. Proceso hoy manual (Excel + Word);
esta app web lo automatiza.

## Comandos (uv siempre, nunca pip)
- `uv sync` — instalar dependencias.
- `uv run python cargar_datos.py` — crear tablas y cargar los Excel a la BD.
- `uv run python app.py` — servidor Flask en puerto 5000.
- `uv run pytest` — pruebas automáticas (`tests/test_app.py`, 4 pruebas; no
  dependen del `.env`: definen sus propias credenciales de prueba).
- Construcción por etapas: ver `PLAN.md` (1 cruce → 2 backend → 3 interfaz).

## Decisiones técnicas (no reabrir sin motivo)
- Excel: `pandas` + `openpyxl` (promedios y agrupados directos; `xlrd` obsoleto
  para .xlsx, `polars` innecesario a esta escala).
- Web: `Flask` + Jinja (app pequeña de 4 rutas; `FastAPI` es para APIs JSON,
  `Django` sobredimensionado, `Streamlit` no da PDFs propios).
- PDF: `fpdf2` en memoria (sin software externo; `weasyprint` exigiría
  instalación del sistema).
- BD dual sin migraciones: SQLite local (`academia.db`) o Supabase según haya
  `DATABASE_URL`; `models/datos.py` abstrae el motor.

## Datos y base de datos
- `Insumos/` es solo lectura: nunca modificarlo. En disco la carpeta lleva mayúscula;
  el código acepta `insumos/` o `Insumos/` (`_resolver_ruta_insumo`): no hardcodear una sola.
- Hojas y columnas exactas: `Maestro_Estudiantes.xlsx` → hoja `Estudiantes`
  (Identificacion, Nombre_Completo, Correo, Programa, Cohorte);
  `Registro_Evaluaciones.xlsx` → hoja `Evaluaciones`
  (Identificacion, Programa, Modulo, Nota, Asistencia_Pct, Fecha_Cierre;
  notas en escala 0–100).
- `Identificacion` siempre como texto con strip en todo el flujo (lectura, BD y reglas).
- Sin `DATABASE_URL` en `.env` la app usa SQLite local (`academia.db`, archivo
  trackeado en git: correr la app lo modifica). Con `DATABASE_URL` usa Supabase
  (PostgreSQL) vía `psycopg` con `prepare_threshold=None` (pooler de Supabase).
- Plantilla de entorno: copiar `.env.ejemplo` a `.env` (`DATABASE_URL`,
  `SECRET_KEY`, `ADMIN_CORREO/ADMIN_CLAVE`, `USUARIO_CORREO/USUARIO_CLAVE`).
  `.env` está en `.gitignore`: nunca se sube. Sin esas credenciales la app usa
  usuarios de demostración y lo avisa en `/login`.
- `models/datos.py` es el ÚNICO archivo que habla con la BD. Usa sus helpers
  (`obtener_conexion`, `es_sqlite`): los placeholders cambian según motor
  (`?` SQLite vs `%s` Postgres). `guardar_*` hace `DELETE` + reinserción total.
- Si la BD está vacía o falla, `models/certificados.py` lee los Excel directo
  como respaldo (`_obtener_datos_origen`).

## Reglas del negocio (`models/certificados.py`)
- R1: agrupar por `identificacion + programa` (un certificado por estudiante
  y programa). R2: promedio de `nota` y de
  `asistencia_pct`, redondeados a 2 decimales.
- R3 Aprobación: promedio ≥ 70 y asistencia ≥ 80 (límites incluidos).
  R4 Participación: promedio < 70 y asistencia ≥ 80. R5 Sin certificado: asistencia < 80.
- R6 Inconsistencias (no certifican, van al panel de alertas): maestro sin
  evaluaciones; evaluaciones sin maestro; asistencia < 50.
- Constantes: `NOTA_MINIMA = 70`, `ASISTENCIA_MINIMA = 80`, `ASISTENCIA_CRITICA = 50`.

## Cifras de control (criterio de aceptación, sin excepciones)
- 19 Aprobación, 3 Participación, 1 Sin certificado, 3 inconsistencias.
- Inconsistencias: `304560321` (Javier Espinoza, sin evaluaciones), `999880777`
  (sin maestro), Fernanda Zúñiga (asistencia 36.25).
- Casos: Camila Rojas Méndez `101230456` = 91.25/96.25 Aprobación;
  Luis Acuña Blanco = 72.0/81.67 Aprobación.

## Arquitectura y límites MVC
- Metáfora del usuario: Bodega = `Insumos/` (+ BD), Cocina = Python/Flask
  (toda la lógica, nunca en la interfaz), Salón = `views/` (solo muestra).
- `app.py` crea `app` (Flask con `template_folder="views"`,
  `static_folder="views/static"`, rutas en blueprint `controllers/certificados.py`).
- Rutas: `/login` y `/salir` (sesión con `session`), `/` tablero con panel de
  administrador (`#panel-admin`), `/cargar` (POST: procesa ambos Excel subidos
  en memoria y recalcula con `accion=ver|descargar`), `/certificado/<id>/<programa>`
  (PDF; 404 si no es certificable), `/descargar-todos` (.zip en memoria),
  `/descargar-excel` (resultados de fábrica en .xlsx).
  Las rutas de datos usan el decorador `requiere_login` (en
  `controllers/auth.py`); la validación de credenciales vive en
  `services/autenticacion.py` y lee variables de entorno.
  `solo_admin` protege `/cargar` y `/descargar-todos` (403 con
  `views/sin_permiso.html`); el rol `usuario` no ve el panel de
  inconsistencias ni los botones de administración.
  Los Excel subidos no se guardan: `procesar_datos_completos` acepta
  `archivo_estudiantes/archivo_evaluaciones` (BytesIO) y, sin ellos, sigue
  leyendo la BD o `Insumos/`. Límite: 4 MB por archivo y 4.5 MB por petición
  (`MAX_CONTENT_LENGTH`); el Excel de resultados se arma en memoria con
  `services/generador_excel.py`.
  `controllers/` solo orquesta (tiene fallbacks si falta la plantilla); la lógica
  vive en `models/` y `services/` (`carga_excel.py`, `generador_pdf.py` con fpdf2,
  A4 horizontal). `views/` solo Jinja: azul marino `#14213D`, dorado `#B8923D`.
- Subagentes en `.agents/agents/`: `backend-flask` (Python, no toca `views/`),
  `disenador-vistas` (solo `views/`, sin lógica), `tester-datos` (prueba y reporta,
  no escribe código), `revisor` (audita con solo lectura).

## Seguridad y trato
- Nunca leer ni mostrar `.env`; nunca hardcodear credenciales o URLs en el código.
- Código simple y comentado en español, señalando los ladrillos (variables,
  tipos, condicionales, bucles, funciones): el usuario está aprendiendo a programar.
- Responder en español sencillo (usuario principiante); antes de construir,
  plan corto y esperar aprobación; entregas pequeñas indicando archivos y capa;
  al cerrar, pasan `tester-datos` y `revisor`.
