from pathlib import Path
from typing import Dict, Optional, Union
import pandas as pd

from models.datos import guardar_estudiantes, guardar_evaluaciones

BASE_DIR = Path(__file__).resolve().parent.parent

COLUMNAS_ESTUDIANTES = [
    "Identificacion",
    "Nombre_Completo",
    "Correo",
    "Programa",
    "Cohorte",
]

COLUMNAS_EVALUACIONES = [
    "Identificacion",
    "Programa",
    "Modulo",
    "Nota",
    "Asistencia_Pct",
    "Fecha_Cierre",
]


def _resolver_ruta_insumo(nombre_archivo: str) -> Path:
    """Busca un archivo dentro de insumos o Insumos de forma insensible a mayúsculas/minúsculas."""
    for carpeta in ["insumos", "Insumos"]:
        posible_ruta = BASE_DIR / carpeta / nombre_archivo
        if posible_ruta.exists():
            return posible_ruta
    return BASE_DIR / "insumos" / nombre_archivo


def procesar_excel_estudiantes(origen: Optional[Union[str, Path, object]] = None) -> int:
    """Lee y procesa el archivo de Maestro de Estudiantes (hoja 'Estudiantes').

    Guarda los registros en Supabase mediante models.datos.guardar_estudiantes.
    Retorna la cantidad de estudiantes guardados.
    """
    if origen is None:
        origen = _resolver_ruta_insumo("Maestro_Estudiantes.xlsx")

    # Leer especificando la hoja y tipos de datos
    df = pd.read_excel(origen, sheet_name="Estudiantes", dtype={"Identificacion": str})

    # Validar columnas requeridas
    columnas_presentes = set(df.columns)
    columnas_faltantes = [col for col in COLUMNAS_ESTUDIANTES if col not in columnas_presentes]
    if columnas_faltantes:
        raise ValueError(
            f"El archivo de Estudiantes no contiene las columnas requeridas: {columnas_faltantes}"
        )

    # Limpieza: Identificación siempre como texto estricto y sin espacios
    df["Identificacion"] = df["Identificacion"].astype(str).str.strip()
    df["Nombre_Completo"] = df["Nombre_Completo"].astype(str).str.strip()
    df["Correo"] = df["Correo"].fillna("").astype(str).str.strip()
    df["Programa"] = df["Programa"].astype(str).str.strip()
    df["Cohorte"] = df["Cohorte"].astype(str).str.strip()

    # Guardar en base de datos
    return guardar_estudiantes(df[COLUMNAS_ESTUDIANTES])


def procesar_excel_evaluaciones(origen: Optional[Union[str, Path, object]] = None) -> int:
    """Lee y procesa el archivo de Registro de Evaluaciones (hoja 'Evaluaciones').

    Guarda los registros en Supabase mediante models.datos.guardar_evaluaciones.
    Retorna la cantidad de evaluaciones guardadas.
    """
    if origen is None:
        origen = _resolver_ruta_insumo("Registro_Evaluaciones.xlsx")

    # Leer especificando la hoja y tipos de datos
    df = pd.read_excel(origen, sheet_name="Evaluaciones", dtype={"Identificacion": str})

    # Validar columnas requeridas
    columnas_presentes = set(df.columns)
    columnas_faltantes = [col for col in COLUMNAS_EVALUACIONES if col not in columnas_presentes]
    if columnas_faltantes:
        raise ValueError(
            f"El archivo de Evaluaciones no contiene las columnas requeridas: {columnas_faltantes}"
        )

    # Limpieza: Identificación siempre como texto estricto y sin espacios
    df["Identificacion"] = df["Identificacion"].astype(str).str.strip()
    df["Programa"] = df["Programa"].astype(str).str.strip()
    df["Modulo"] = df["Modulo"].astype(str).str.strip()

    # Formatear Fecha_Cierre
    if "Fecha_Cierre" in df.columns:
        df["Fecha_Cierre"] = pd.to_datetime(df["Fecha_Cierre"], errors="coerce").dt.strftime("%Y-%m-%d")

    # Guardar en base de datos
    return guardar_evaluaciones(df[COLUMNAS_EVALUACIONES])


def cargar_datos_completos(
    ruta_estudiantes: Optional[Union[str, Path, object]] = None,
    ruta_evaluaciones: Optional[Union[str, Path, object]] = None,
) -> Dict[str, int]:
    """Carga ambos archivos Excel y almacena sus registros en Supabase."""
    total_estudiantes = procesar_excel_estudiantes(ruta_estudiantes)
    total_evaluaciones = procesar_excel_evaluaciones(ruta_evaluaciones)
    return {
        "estudiantes": total_estudiantes,
        "evaluaciones": total_evaluaciones,
    }
