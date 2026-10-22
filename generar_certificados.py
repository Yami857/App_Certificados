import re
import sys
from pathlib import Path

from models.certificados import procesar_datos_completos
from services.generador_pdf import generar_pdf_certificado

# Carpeta donde se dejan los PDF (se crea sola si no existe)
CARPETA_SALIDA = Path(__file__).parent / "certificados"


def limpiar_nombre_archivo(texto: str) -> str:
    """Convierte un texto en un nombre de archivo seguro (igual regla que la web)."""
    cadena = str(texto).strip()
    cadena = re.sub(r"[^\w\s-]", "", cadena)
    return re.sub(r"[-\s]+", "_", cadena)


def main():
    print("Generando certificados en PDF...")

    # 1. Aplicar las reglas de negocio (R1 a R6) y obtener solo los certificables
    datos = procesar_datos_completos()
    certificables = datos["certificables"]  # lista de diccionarios
    resumen = datos["resumen"]

    if not certificables:
        print("[AVISO] No hay estudiantes certificables.", file=sys.stderr)
        sys.exit(1)

    # 2. Crear la carpeta de salida
    CARPETA_SALIDA.mkdir(exist_ok=True)

    # 3. Recorrer la lista y escribir un PDF por estudiante
    generados = 0
    for estudiante in certificables:
        pdf_bytes = generar_pdf_certificado(estudiante)

        slug_programa = limpiar_nombre_archivo(estudiante["programa"])
        nombre_archivo = f"Certificado_{estudiante['identificacion']}_{slug_programa}.pdf"
        ruta = CARPETA_SALIDA / nombre_archivo

        ruta.write_bytes(pdf_bytes)
        generados += 1
        print(f"  - {nombre_archivo}")

    # 4. Mostrar el resumen de control para comparar con AGENTS.md
    print("\n=== Resumen ===")
    print(f"Aprobación:        {resumen['aprobacion']}")
    print(f"Participación:     {resumen['participacion']}")
    print(f"Sin certificado:   {resumen['sin_certificado']}")
    print(f"Inconsistencias:   {resumen['inconsistencias']}")
    print(f"PDF generados:     {generados}")
    print(f"Carpeta:           {CARPETA_SALIDA}")
    print("===============")


if __name__ == "__main__":
    main()
