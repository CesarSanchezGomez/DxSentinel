# scripts/generate_golden_record.py
"""
Script simplificado para generar golden_record_template.csv únicamente.
"""
import sys
from pathlib import Path
from datetime import datetime

# ================= CONFIGURACIÓN =================
LANGUAGE_CODE = "en-US"  # Opciones: "es", "es-mx", "en", "en-us", "fr", etc.
# =================================================

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from parsing import parse_successfactors_xml
from generators.golden_record import GoldenRecordGenerator


def get_absolute_path(relative_path: str) -> Path:
    """Convierte ruta relativa a absoluta desde la raíz del proyecto."""
    return PROJECT_ROOT / relative_path


def main():
    """Función principal del script."""
    XML_FILE = get_absolute_path("data/xml/sdm_español.xml")
    OUTPUT_DIR = get_absolute_path("output/golden_record")

    try:
        print("=" * 60)
        print("GENERADOR DE GOLDEN RECORD TEMPLATE")
        print(f"Idioma configurado: {LANGUAGE_CODE}")
        print("=" * 60)

        # 1. Verificar archivo
        print(f"\n1. Verificando archivo: {XML_FILE.name}")

        if not XML_FILE.exists():
            print(f"ERROR: Archivo no encontrado")
            print(f"Ruta buscada: {XML_FILE.absolute()}")

            data_dir = get_absolute_path("data")
            if data_dir.exists():
                print(f"\nArchivos XML en {data_dir}:")
                for file in data_dir.glob("*.xml"):
                    print(f"  - {file.name}")

            print("\nSoluciones:")
            print(f"  1. Coloca tu archivo XML en: {data_dir.absolute()}/")
            print(f"  2. Modifica la variable XML_FILE en este script")
            return

        print(f"   Archivo encontrado ({XML_FILE.stat().st_size} bytes)")

        # 2. Parsear XML
        print(f"\n2. Parseando SDM...")
        parsed_model = parse_successfactors_xml(str(XML_FILE), "golden_record")
        print("   SDM parseado correctamente")

        # 3. Generar template
        print(f"\n3. Generando template CSV")
        print(f"   Directorio: {OUTPUT_DIR}")
        print(f"   Idioma: {LANGUAGE_CODE}")

        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        generator = GoldenRecordGenerator(output_dir=str(OUTPUT_DIR))

        start_time = datetime.now()
        template_file = generator.generate_template(
            parsed_model=parsed_model,
            language_code=LANGUAGE_CODE
        )
        end_time = datetime.now()

        # 4. Mostrar resultados
        print(f"\n4. RESULTADO:")
        print("-" * 40)

        template_path = Path(template_file)
        if template_path.exists():
            file_size = template_path.stat().st_size
            print(f"   Archivo: {template_path.name}")
            print(f"   Ruta: {template_path}")
            print(f"   Tamaño: {file_size / 1024:.1f} KB")
            print(f"   Tiempo: {(end_time - start_time).total_seconds():.2f}s")
        else:
            print(f"   ERROR: Archivo no generado")

        print("\n" + "=" * 60)
        print(f"PROCESO COMPLETADO - Idioma: {LANGUAGE_CODE}")
        print("=" * 60)

    except Exception as e:
        print(f"\nERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
