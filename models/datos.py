import os
import sqlite3
from pathlib import Path
from typing import Any, Dict, List, Union
from dotenv import load_dotenv

# Cargar variables de entorno al iniciar el módulo
load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent
SQLITE_DB_PATH = BASE_DIR / "academia.db"


def es_sqlite() -> bool:
    """Determina si se debe usar SQLite local en lugar de Supabase/PostgreSQL."""
    load_dotenv()
    db_url = os.getenv("DATABASE_URL")
    if not db_url or not db_url.strip() or "sqlite" in db_url.lower():
        return True
    return False


def obtener_conexion():
    """Obtiene una conexión a Supabase (PostgreSQL) o a SQLite local si no hay DATABASE_URL configurada."""
    load_dotenv()
    db_url = os.getenv("DATABASE_URL")
    if es_sqlite():
        # Conexión local a SQLite
        conn = sqlite3.connect(str(SQLITE_DB_PATH))
        conn.row_factory = sqlite3.Row
        return conn

    # Conexión a Supabase con psycopg y pooler
    import psycopg
    return psycopg.connect(db_url, prepare_threshold=None)


def crear_tablas():
    """Crea las tablas estudiantes y evaluaciones si no existen."""
    usa_sqlite = es_sqlite()

    if usa_sqlite:
        sql_estudiantes = """
        CREATE TABLE IF NOT EXISTS estudiantes (
            identificacion TEXT PRIMARY KEY,
            nombre_completo TEXT,
            correo TEXT,
            programa TEXT,
            cohorte TEXT
        );
        """
        sql_evaluaciones = """
        CREATE TABLE IF NOT EXISTS evaluaciones (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            identificacion TEXT,
            programa TEXT,
            modulo TEXT,
            nota REAL,
            asistencia_pct REAL,
            fecha_cierre TEXT
        );
        """
    else:
        sql_estudiantes = """
        CREATE TABLE IF NOT EXISTS estudiantes (
            identificacion TEXT PRIMARY KEY,
            nombre_completo TEXT,
            correo TEXT,
            programa TEXT,
            cohorte TEXT
        );
        """
        sql_evaluaciones = """
        CREATE TABLE IF NOT EXISTS evaluaciones (
            id SERIAL PRIMARY KEY,
            identificacion TEXT,
            programa TEXT,
            modulo TEXT,
            nota NUMERIC(5,2),
            asistencia_pct NUMERIC(5,2),
            fecha_cierre TEXT
        );
        """

    conn = obtener_conexion()
    try:
        cur = conn.cursor()
        cur.execute(sql_estudiantes)
        cur.execute(sql_evaluaciones)
        conn.commit()
    finally:
        conn.close()


def guardar_estudiantes(datos: Union[List[Dict[str, Any]], Any]) -> int:
    """Reemplaza los registros de la tabla estudiantes con los nuevos datos suministrados.

    datos puede ser una lista de diccionarios o un DataFrame de pandas.
    Retorna la cantidad de registros insertados.
    """
    if hasattr(datos, "to_dict"):
        registros = datos.to_dict(orient="records")
    else:
        registros = list(datos)

    filas_a_insertar = []
    for reg in registros:
        identificacion = str(reg.get("Identificacion") or reg.get("identificacion") or "").strip()
        nombre_completo = str(reg.get("Nombre_Completo") or reg.get("nombre_completo") or "").strip()
        correo = str(reg.get("Correo") or reg.get("correo") or "").strip()
        programa = str(reg.get("Programa") or reg.get("programa") or "").strip()
        cohorte = str(reg.get("Cohorte") or reg.get("cohorte") or "").strip()

        filas_a_insertar.append((
            identificacion,
            nombre_completo,
            correo,
            programa,
            cohorte,
        ))

    placeholder = "?" if es_sqlite() else "%s"
    sql_insert = f"""
    INSERT INTO estudiantes (
        identificacion,
        nombre_completo,
        correo,
        programa,
        cohorte
    ) VALUES ({placeholder}, {placeholder}, {placeholder}, {placeholder}, {placeholder});
    """

    conn = obtener_conexion()
    try:
        cur = conn.cursor()
        cur.execute("DELETE FROM estudiantes;")
        if filas_a_insertar:
            cur.executemany(sql_insert, filas_a_insertar)
        conn.commit()
    finally:
        conn.close()

    return len(filas_a_insertar)


def guardar_evaluaciones(datos: Union[List[Dict[str, Any]], Any]) -> int:
    """Reemplaza los registros de la tabla evaluaciones con los nuevos datos suministrados.

    datos puede ser una lista de diccionarios o un DataFrame de pandas.
    Retorna la cantidad de registros insertados.
    """
    if hasattr(datos, "to_dict"):
        registros = datos.to_dict(orient="records")
    else:
        registros = list(datos)

    filas_a_insertar = []
    for reg in registros:
        identificacion = str(reg.get("Identificacion") or reg.get("identificacion") or "").strip()
        programa = str(reg.get("Programa") or reg.get("programa") or "").strip()
        modulo = str(reg.get("Modulo") or reg.get("modulo") or "").strip()

        nota_val = reg.get("Nota") if "Nota" in reg else reg.get("nota")
        try:
            nota = float(nota_val) if nota_val is not None else None
        except (ValueError, TypeError):
            nota = None

        asistencia_val = reg.get("Asistencia_Pct") if "Asistencia_Pct" in reg else reg.get("asistencia_pct")
        try:
            asistencia_pct = float(asistencia_val) if asistencia_val is not None else None
        except (ValueError, TypeError):
            asistencia_pct = None

        fecha_val = reg.get("Fecha_Cierre") if "Fecha_Cierre" in reg else reg.get("fecha_cierre")
        if fecha_val is not None:
            fecha_cierre = str(fecha_val).split("T")[0].split(" ")[0].strip()
        else:
            fecha_cierre = None

        filas_a_insertar.append((
            identificacion,
            programa,
            modulo,
            nota,
            asistencia_pct,
            fecha_cierre,
        ))

    placeholder = "?" if es_sqlite() else "%s"
    sql_insert = f"""
    INSERT INTO evaluaciones (
        identificacion,
        programa,
        modulo,
        nota,
        asistencia_pct,
        fecha_cierre
    ) VALUES ({placeholder}, {placeholder}, {placeholder}, {placeholder}, {placeholder}, {placeholder});
    """

    conn = obtener_conexion()
    try:
        cur = conn.cursor()
        cur.execute("DELETE FROM evaluaciones;")
        if filas_a_insertar:
            cur.executemany(sql_insert, filas_a_insertar)
        conn.commit()
    finally:
        conn.close()

    return len(filas_a_insertar)


def contar_estudiantes() -> int:
    """Retorna el número total de registros en la tabla estudiantes."""
    conn = obtener_conexion()
    try:
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM estudiantes;")
        resultado = cur.fetchone()
        return int(resultado[0]) if resultado else 0
    finally:
        conn.close()


def contar_evaluaciones() -> int:
    """Retorna el número total de registros en la tabla evaluaciones."""
    conn = obtener_conexion()
    try:
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM evaluaciones;")
        resultado = cur.fetchone()
        return int(resultado[0]) if resultado else 0
    finally:
        conn.close()


def obtener_estudiantes() -> List[Dict[str, Any]]:
    """Obtiene todos los estudiantes almacenados en la base de datos."""
    conn = obtener_conexion()
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT identificacion, nombre_completo, correo, programa, cohorte FROM estudiantes ORDER BY identificacion;"
        )
        filas = cur.fetchall()
        return [
            {
                "identificacion": f[0],
                "nombre_completo": f[1],
                "correo": f[2],
                "programa": f[3],
                "cohorte": f[4],
            }
            for f in filas
        ]
    finally:
        conn.close()


def obtener_evaluaciones() -> List[Dict[str, Any]]:
    """Obtiene todas las evaluaciones almacenadas en la base de datos."""
    conn = obtener_conexion()
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT id, identificacion, programa, modulo, nota, asistencia_pct, fecha_cierre FROM evaluaciones ORDER BY id;"
        )
        filas = cur.fetchall()
        return [
            {
                "id": f[0],
                "identificacion": f[1],
                "programa": f[2],
                "modulo": f[3],
                "nota": float(f[4]) if f[4] is not None else None,
                "asistencia_pct": float(f[5]) if f[5] is not None else None,
                "fecha_cierre": str(f[6]) if f[6] is not None else None,
            }
            for f in filas
        ]
    finally:
        conn.close()
