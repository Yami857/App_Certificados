from io import BytesIO
from typing import Any, Dict

import pandas as pd

# Columnas del reporte de resultados, en el mismo orden en que se exportan.
COLUMNAS_RESULTADOS = [
    "Identificacion",
    "Nombre_Completo",
    "Correo",
    "Programa",
    "Cohorte",
    "Promedio",
    "Asistencia_Pct",
    "Estado",
    "Tipo_Certificado",
    "Puede_Certificar",
    "Motivo_Inconsistencia",
]


def generar_excel_resultados(datos: Dict[str, Any]) -> bytes:
    """Arma en memoria un Excel con los resultados del procesamiento.

    `datos` es lo que devuelve `models.certificados.procesar_datos_completos`.
    Devuelve los bytes del archivo .xlsx, listos para enviar con send_file.
    No escribe nada en disco (Vercel no lo permite).
    """

    # 1. Una fila por estudiante clasificado
    filas = []
    for estudiante in datos.get("estudiantes_clasificados", []):
        filas.append(
            {
                "Identificacion": estudiante.get("identificacion", ""),
                "Nombre_Completo": estudiante.get("nombre_completo", ""),
                "Correo": estudiante.get("correo", ""),
                "Programa": estudiante.get("programa", ""),
                "Cohorte": estudiante.get("cohorte", ""),
                "Promedio": estudiante.get("promedio"),
                "Asistencia_Pct": estudiante.get("asistencia"),
                "Estado": estudiante.get("estado", ""),
                "Tipo_Certificado": estudiante.get("tipo_certificado") or "",
                "Puede_Certificar": "Sí" if estudiante.get("puede_certificar") else "No",
                "Motivo_Inconsistencia": estudiante.get("motivo_inconsistencia", ""),
            }
        )

    df_resultados = pd.DataFrame(filas, columns=COLUMNAS_RESULTADOS)

    # 2. Hoja de resumen con los conteos oficiales
    resumen = datos.get("resumen", {})
    df_resumen = pd.DataFrame(
        [
            {"Indicador": "Aprobación", "Total": resumen.get("aprobacion", 0)},
            {"Indicador": "Participación", "Total": resumen.get("participacion", 0)},
            {"Indicador": "Sin certificado", "Total": resumen.get("sin_certificado", 0)},
            {"Indicador": "Inconsistencias", "Total": resumen.get("inconsistencias", 0)},
            {"Indicador": "Total certificables", "Total": resumen.get("total_certificables", 0)},
            {"Indicador": "Filas exportadas", "Total": len(df_resultados)},
        ]
    )

    # 3. Escribir ambas hojas en un archivo que vive en memoria
    buffer = BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        df_resultados.to_excel(writer, index=False, sheet_name="Resultados")
        df_resumen.to_excel(writer, index=False, sheet_name="Resumen")

    return buffer.getvalue()
