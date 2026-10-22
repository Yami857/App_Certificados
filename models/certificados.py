import math
from typing import Any, Dict, List, Optional, Tuple
import pandas as pd

from models.datos import obtener_estudiantes, obtener_evaluaciones
from services.carga_excel import (
    _resolver_ruta_insumo,
    leer_estudiantes,
    leer_evaluaciones,
)

# Constantes oficiales de reglas de negocio según AGENTS.md
NOTA_MINIMA = 70.0
ASISTENCIA_MINIMA = 80.0
ASISTENCIA_CRITICA = 50.0


def _dataframes_a_listas(
    df_m: pd.DataFrame,
    df_e: pd.DataFrame,
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """Convierte las dos hojas de Excel en listas de diccionarios.

    Las listas son el formato que consumen las reglas de negocio (R1 a R6).
    """
    estudiantes = [
        {
            "identificacion": str(r["Identificacion"]).strip(),
            "nombre_completo": str(r["Nombre_Completo"]).strip(),
            "correo": str(r.get("Correo", "")).strip(),
            "programa": str(r["Programa"]).strip(),
            "cohorte": str(r.get("Cohorte", "")).strip(),
        }
        for _, r in df_m.iterrows()
    ]

    evaluaciones = [
        {
            "id": idx + 1,
            "identificacion": str(r["Identificacion"]).strip(),
            "programa": str(r["Programa"]).strip(),
            "modulo": str(r["Modulo"]).strip(),
            "nota": float(r["Nota"]) if pd.notna(r["Nota"]) else None,
            "asistencia_pct": float(r["Asistencia_Pct"]) if pd.notna(r["Asistencia_Pct"]) else None,
            "fecha_cierre": str(r.get("Fecha_Cierre", "")).strip(),
        }
        for idx, r in df_e.iterrows()
    ]

    return estudiantes, evaluaciones


def _obtener_datos_origen(
    archivo_estudiantes: Optional[object] = None,
    archivo_evaluaciones: Optional[object] = None,
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """Obtiene los datos de estudiantes y evaluaciones.

    - Si se reciben archivos (por ejemplo BytesIO con un Excel subido), los lee
      en memoria y NO toca la base de datos: sirve para recalcular al vuelo.
    - Si no se recibe nada, usa la base de datos y, si está vacía o falla, lee
      los Excel de la carpeta Insumos (datos de fábrica).
    """
    if archivo_estudiantes is not None or archivo_evaluaciones is not None:
        # Lectura directa de lo subido, sin guardar en disco ni en la base.
        df_m = leer_estudiantes(archivo_estudiantes)
        df_e = leer_evaluaciones(archivo_evaluaciones)
        return _dataframes_a_listas(df_m, df_e)

    try:
        estudiantes = obtener_estudiantes()
        evaluaciones = obtener_evaluaciones()
        if estudiantes and evaluaciones:
            return estudiantes, evaluaciones
    except Exception:
        pass

    # Si la base de datos aún no tiene registros o no está disponible, leer desde los insumos
    ruta_m = _resolver_ruta_insumo("Maestro_Estudiantes.xlsx")
    ruta_e = _resolver_ruta_insumo("Registro_Evaluaciones.xlsx")

    df_m = leer_estudiantes(ruta_m)
    df_e = leer_evaluaciones(ruta_e)

    return _dataframes_a_listas(df_m, df_e)


def procesar_datos_completos(
    estudiantes: Optional[List[Dict[str, Any]]] = None,
    evaluaciones: Optional[List[Dict[str, Any]]] = None,
    archivo_estudiantes: Optional[object] = None,
    archivo_evaluaciones: Optional[object] = None,
) -> Dict[str, Any]:
    """Aplica todas las reglas de negocio (R1 a R6) y clasifica los estudiantes.

    Si no se pasan listas ni archivos, lee los datos de fábrica (base o Insumos).
    Si se pasan archivos en memoria, recalcula con esos datos sin guardarlos.

    Retorna un diccionario estructurado con:
    - 'resumen': conteos oficiales de control (aprobacion, participacion, sin_certificado, inconsistencias)
    - 'estudiantes_clasificados': lista con todos los registros procesados
    - 'inconsistencias': lista con las inconsistencias detalladas
    - 'certificables': lista de estudiantes elegibles para certificado (aprobacion + participacion)
    """
    if estudiantes is None or evaluaciones is None:
        estudiantes, evaluaciones = _obtener_datos_origen(
            archivo_estudiantes,
            archivo_evaluaciones,
        )

    # Indexar maestro por (identificacion, programa)
    maestro_dict: Dict[Tuple[str, str], Dict[str, Any]] = {}
    for est in estudiantes:
        key = (str(est["identificacion"]).strip(), str(est["programa"]).strip())
        maestro_dict[key] = est

    # R1: Agrupar evaluaciones por (identificacion, programa)
    eval_agrupadas: Dict[Tuple[str, str], List[Dict[str, Any]]] = {}
    for ev in evaluaciones:
        key = (str(ev["identificacion"]).strip(), str(ev["programa"]).strip())
        if key not in eval_agrupadas:
            eval_agrupadas[key] = []
        eval_agrupadas[key].append(ev)

    # R2: Calcular promedios de nota y asistencia redondeados a 2 decimales
    metricas_eval: Dict[Tuple[str, str], Dict[str, Any]] = {}
    for key, lista_ev in eval_agrupadas.items():
        notas = [ev["nota"] for ev in lista_ev if ev.get("nota") is not None]
        asistencias = [ev["asistencia_pct"] for ev in lista_ev if ev.get("asistencia_pct") is not None]

        promedio_nota = round(sum(notas) / len(notas), 2) if notas else 0.0
        promedio_asist = round(sum(asistencias) / len(asistencias), 2) if asistencias else 0.0

        metricas_eval[key] = {
            "promedio": promedio_nota,
            "asistencia": promedio_asist,
            "cantidad_modulos": len(lista_ev),
        }

    todas_las_llaves = set(maestro_dict.keys()) | set(metricas_eval.keys())

    registros_clasificados = []
    lista_inconsistencias = []
    certificables = []

    conteo_aprobacion = 0
    conteo_participacion = 0
    conteo_sin_certificado = 0

    for key in sorted(todas_las_llaves, key=lambda k: (k[0], k[1])):
        identificacion, programa = key
        en_maestro = key in maestro_dict
        en_evaluaciones = key in metricas_eval

        est_info = maestro_dict.get(key, {})
        nombre_completo = est_info.get("nombre_completo", "")
        correo = est_info.get("correo", "")
        cohorte = est_info.get("cohorte", "")

        eval_info = metricas_eval.get(key, {})
        promedio = eval_info.get("promedio", None)
        asistencia = eval_info.get("asistencia", None)

        es_inconsistencia = False
        motivo_inconsistencia = ""
        estado = ""
        tipo_certificado = None  # "Aprobación", "Participación" o None
        puede_certificar = False

        # R6: Inconsistencias
        if en_maestro and not en_evaluaciones:
            # Caso 1: Estudiante del maestro sin evaluaciones (Ej: Javier Espinoza 304560321)
            es_inconsistencia = True
            motivo_inconsistencia = "Estudiante registrado en el maestro pero sin evaluaciones."
            estado = "Inconsistencia"
        elif en_evaluaciones and not en_maestro:
            # Caso 2: Identificación con evaluaciones que no está en el maestro (Ej: 999880777)
            es_inconsistencia = True
            motivo_inconsistencia = "Evaluaciones registradas pero ausente en el maestro de estudiantes."
            estado = "Inconsistencia"
        else:
            # Presente en ambos: Evaluar asistencia y nota
            if asistencia is not None and asistencia < ASISTENCIA_CRITICA:
                # Caso 3: Asistencia menor a 50 % (Ej: Fernanda Zúñiga 36.25 %)
                es_inconsistencia = True
                motivo_inconsistencia = f"Asistencia crítica ({asistencia}%), inferior al 50 %."

            # R3: Aprobación: promedio >= 70 y asistencia >= 80
            if asistencia >= ASISTENCIA_MINIMA and promedio >= NOTA_MINIMA:
                estado = "Aprobación"
                tipo_certificado = "Certificado de Aprobación"
                puede_certificar = True
                conteo_aprobacion += 1
            # R4: Participación: promedio < 70 y asistencia >= 80
            elif asistencia >= ASISTENCIA_MINIMA and promedio < NOTA_MINIMA:
                estado = "Participación"
                tipo_certificado = "Certificado de Participación"
                puede_certificar = True
                conteo_participacion += 1
            # R5: Sin certificado: asistencia < 80
            elif asistencia < ASISTENCIA_MINIMA:
                estado = "Sin certificado"
                puede_certificar = False
                conteo_sin_certificado += 1

        registro = {
            "identificacion": identificacion,
            "nombre_completo": nombre_completo,
            "correo": correo,
            "programa": programa,
            "cohorte": cohorte,
            "promedio": promedio,
            "asistencia": asistencia,
            "estado": estado,
            "tipo_certificado": tipo_certificado,
            "puede_certificar": puede_certificar,
            "es_inconsistencia": es_inconsistencia,
            "motivo_inconsistencia": motivo_inconsistencia,
        }

        registros_clasificados.append(registro)

        if es_inconsistencia:
            lista_inconsistencias.append({
                "identificacion": identificacion,
                "nombre_completo": nombre_completo or "(No registrado)",
                "programa": programa,
                "motivo": motivo_inconsistencia,
                "promedio": promedio,
                "asistencia": asistencia,
            })

        if puede_certificar and not es_inconsistencia:
            certificables.append(registro)

    resumen = {
        "aprobacion": conteo_aprobacion,
        "participacion": conteo_participacion,
        "sin_certificado": conteo_sin_certificado,
        "inconsistencias": len(lista_inconsistencias),
        "total_certificables": len(certificables),
    }

    return {
        "resumen": resumen,
        "estudiantes_clasificados": registros_clasificados,
        "inconsistencias": lista_inconsistencias,
        "certificables": certificables,
    }


def obtener_certificado_individual(
    identificacion: str,
    programa: str,
) -> Optional[Dict[str, Any]]:
    """Busca y retorna los datos del estudiante solo si es elegible para certificado.

    Si tiene 'Sin certificado' o es una 'Inconsistencia', retorna None.
    """
    datos = procesar_datos_completos()
    identificacion_limpia = str(identificacion).strip()
    programa_limpio = str(programa).strip().lower()

    for cert in datos["certificables"]:
        if (
            cert["identificacion"] == identificacion_limpia
            and cert["programa"].strip().lower() == programa_limpio
        ):
            return cert

    return None
