# PLAN.md — Construcción por etapas (App de Certificados, Academia Horizonte)

## Punto de partida
El repo ya trae una implementación completa (app.py, models/, services/,
controllers/, views/). No se reescribe desde cero: cada etapa **verifica y
completa** lo existente contra las cifras de control de AGENTS.md
(19 Aprobación, 3 Participación, 1 Sin certificado, 3 inconsistencias).
Si algo no cuadra, se corrige en su capa antes de seguir.

## Etapa 1 — Validar el cruce de datos (Bodega)
**Qué hacer:**
1. Lectura solo-lectura de los 2 Excel (Identificacion como texto + strip).
2. Agrupar evaluaciones por identificacion + programa; promedio de nota y de
   asistencia (redondeo 2 decimales; dividir entre módulos cursados: 4 en
   Técnico en IA, 3 en Excel Avanzado).
3. Aplicar R1–R6 y listar: certificables por tipo + 3 inconsistencias
   (`304560321` sin evaluaciones, `999880777` sin maestro, Zúñiga 36.25).
**Validar antes de seguir:**
- Cifras exactas 19/3/1/3 y casos Camila `101230456` (91.25/96.25),
  Acuña `402340178` (72.0/81.67). Sin esto no se avanza.
- `Insumos/` intacto (git status limpio en esa carpeta).

## Etapa 2 — Backend con Flask (Cocina)
**Qué hacer (en este orden):**
1. `models/datos.py`: conexión (SQLite local sin `DATABASE_URL`, Supabase con
   `psycopg` + `prepare_threshold=None` si existe) y tablas.
2. `services/carga_excel.py` + `cargar_datos.py`: carga de ambos Excel a la BD.
3. `models/certificados.py`: reglas como funciones puras (mismas R1–R6).
4. `controllers/`: rutas `/`, `/cargar`, `/certificado/<id>/<programa>`,
   `/descargar-todos`; `services/generador_pdf.py` (fpdf2, A4 horizontal).
**Validar antes de seguir:**
- `uv run python cargar_datos.py` carga 24 estudiantes + 88 evaluaciones.
- `uv run python app.py` (puerto 5000): `/` muestra 19/3/1/3; el PDF de
  `101230456` descarga; un Sin certificado y un inexistente devuelven 404;
  el `.zip` trae 22 PDF.
- Toda la lógica en Python; nada de cálculos en plantillas.

## Etapa 3 — Interfaz (Salón)
**Qué hacer:**
1. `views/index.html`: tablero (métricas, tabla con descarga por fila, botón
   .zip masivo, panel de alertas de inconsistencias).
2. `views/cargar.html`: formulario de subida de los 2 Excel.
3. Estilo azul marino `#14213D` + dorado `#B8923D`, responsivo.
**Validar antes de seguir:**
- Revisión visual de las 2 páginas + flujo completo: subir Excel → ver
  tablero → descargar 1 PDF → descargar .zip.
- Cifras del tablero = cifras de la Etapa 1.

## Reglas de todas las etapas
- `uv` siempre (nunca pip). No tocar `Insumos/`. No leer/mostrar `.env`.
- Código simple, comentado en español (variables, tipos, condicionales,
  bucles, funciones). Explicaciones en español sencillo.
- Entregas pequeñas indicando archivos y capa (Bodega/Cocina/Salón).
- Cierre de etapa: `tester-datos` prueba (esperado vs. obtenido) y `revisor`
  audita (MVC + sin secretos). Solo entonces sigue la etapa siguiente.
