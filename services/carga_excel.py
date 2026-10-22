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


def leer_estudiantes(origen: Union[str, Path, object]) -> pd.DataFrame:
    """Lee y limpia la hoja 'Estudiantes' sin guardar nada en la base de datos.

    `origen` puede ser una ruta a un Excel o un archivo en memoria (BytesIO).
    Devuelve solo las columnas obligatorias, con la identificación como texto.
    """
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

    return df[COLUMNAS_ESTUDIANTES]


def leer_evaluaciones(origen: Union[str, Path, object]) -> pd.DataFrame:
    """Lee y limpia la hoja 'Evaluaciones' sin guardar nada en la base de datos.

    `origen` puede ser una ruta a un Excel o un archivo en memoria (BytesIO).
    """
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

    return df[COLUMNAS_EVALUACIONES]


def procesar_excel_estudiantes(origen: Optional[Union[str, Path, object]] = None) -> int:
    """Lee el Maestro de Estudiantes y lo guarda en la base de datos.

    Si no se indica `origen`, usa el Excel de la carpeta Insumos.
    Retorna la cantidad de estudiantes guardados.
    """
    if origen is None:
        origen = _resolver_ruta_insumo("Maestro_Estudiantes.xlsx")

    df = leer_estudiantes(origen)
    return guardar_estudiantes(df[COLUMNAS_ESTUDIANTES])


def procesar_excel_evaluaciones(origen: Optional[Union[str, Path, object]] = None) -> int:
    """Lee el Registro de Evaluaciones y lo guarda en la base de datos.

    Si no se indica `origen`, usa el Excel de la carpeta Insumos.
    Retorna la cantidad de evaluaciones guardadas.
    """
    if origen is None:
        origen = _resolver_ruta_insumo("Registro_Evaluaciones.xlsx")

    df = leer_evaluaciones(origen)
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
