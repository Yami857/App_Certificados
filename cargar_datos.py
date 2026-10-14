import sys
from models.datos import contar_estudiantes, contar_evaluaciones, crear_tablas
from services.carga_excel import cargar_datos_completos


def main():
    print("Iniciando proceso de carga de datos...")
    try:
        # 1. Asegurar la existencia de las tablas
        print("- Creando o verificando tablas en la base de datos...")
        crear_tablas()
        print("  Tablas verificadas correctamente.")

        # 2. Cargar los datos desde los archivos Excel
        print("- Leyendo insumos Excel y cargando datos a Supabase...")
        resumen_carga = cargar_datos_completos()
        print(f"  Registros procesados del Excel: {resumen_carga['estudiantes']} estudiantes, {resumen_carga['evaluaciones']} evaluaciones.")

        # 3. Consultar y verificar el conteo en base de datos
        total_estudiantes = contar_estudiantes()
        total_evaluaciones = contar_evaluaciones()

        print("\n=== Resultado de la Carga de Datos ===")
        print(f"Total de estudiantes en base de datos: {total_estudiantes}")
        print(f"Total de evaluaciones en base de datos: {total_evaluaciones}")
        print("======================================\n")

        print("Carga de datos finalizada con éxito.")
    except Exception as e:
        print(f"\n[ERROR] Ocurrió un fallo durante la carga de datos: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
