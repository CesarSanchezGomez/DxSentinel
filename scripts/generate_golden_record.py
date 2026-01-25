"""Script simplificado para generar golden_record_template.csv únicamente."""
import sys
from pathlib import Path
from datetime import datetime

# ================= CONFIGURACIÓN =================
LANGUAGE_CODE = "es-MEX"  # Opciones: "es", "es-mx", "en", "en-us", "fr", etc.
COUNTRY_CODE = "MEX"    # Código de país específico (ej: "MEX", "USA", "BRA")
                        # Dejar como None o "" para incluir todos los países
# =================================================

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from parsing import parse_successfactors_with_csf
from generators.golden_record import GoldenRecordGenerator


def get_absolute_path(relative_path: str) -> Path:
    """Convierte ruta relativa a absoluta desde la raíz del proyecto."""
    return PROJECT_ROOT / relative_path


def main():
    """Función principal del script."""
    MAIN_XML_FILE = get_absolute_path("data/xml/sdm_español.xml")
    CSF_XML_FILE = get_absolute_path("data/xml/csf_español.xml")  # Archivo con campos por país
    OUTPUT_DIR = get_absolute_path("output/golden_record")

    try:
        print("=" * 60)
        print("GENERADOR DE GOLDEN RECORD TEMPLATE")
        print(f"Idioma configurado: {LANGUAGE_CODE}")
        if COUNTRY_CODE:
            print(f"País filtrado: {COUNTRY_CODE}")
        else:
            print("Modo: Todos los países")
        print("=" * 60)

        # 1. Verificar archivos
        print(f"\n1. Verificando archivos...")
        
        if not MAIN_XML_FILE.exists():
            print(f"ERROR: Archivo principal no encontrado")
            print(f"Ruta: {MAIN_XML_FILE.absolute()}")
            
            data_dir = get_absolute_path("data")
            if data_dir.exists():
                print(f"\nArchivos XML en {data_dir}:")
                for file in data_dir.rglob("*.xml"):
                    print(f"  - {file.relative_to(data_dir)}")
            
            return

        print(f"  Archivo principal: {MAIN_XML_FILE.name}")
        
        use_csf = True
        if not CSF_XML_FILE.exists():
            print(f"  Archivo CSF no encontrado: {CSF_XML_FILE.name}")
            print(f"  Continuando solo con archivo principal")
            use_csf = False
        else:
            print(f"  Archivo CSF: {CSF_XML_FILE.name}")

        # 2. Parsear XML
        print(f"\n2. Parseando SDM...")
        try:
            if use_csf:
                print(f"  Fusionando con CSF...")
                parsed_model = parse_successfactors_with_csf(
                    str(MAIN_XML_FILE), 
                    str(CSF_XML_FILE)
                )
            else:
                from parsing.xml_loader import XMLLoader
                from parsing.xml_parser import XMLParser
                from parsing.xml_normalizer import XMLNormalizer
                
                loader = XMLLoader()
                parser = XMLParser()
                normalizer = XMLNormalizer()
                
                root = loader.load_from_file(str(MAIN_XML_FILE), "golden_record")
                document = parser.parse_document(root, "golden_record")
                parsed_model = normalizer.normalize_document(document)
            
            print("  SDM parseado correctamente")
            
        except Exception as parse_error:
            print(f"  Error parseando XML: {parse_error}")
            raise

        # 3. Generar template
        print(f"\n3. Generando template CSV")
        print(f"  Directorio: {OUTPUT_DIR}")
        print(f"  Idioma: {LANGUAGE_CODE}")
        if COUNTRY_CODE:
            print(f"  País: {COUNTRY_CODE}")

        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        
        target_country = COUNTRY_CODE if COUNTRY_CODE else None
        
        generator = GoldenRecordGenerator(
            output_dir=str(OUTPUT_DIR),
            target_country=target_country
        )

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
            
            with open(template_path, 'r', encoding='utf-8-sig') as f:
                lines = f.readlines()
                if lines and len(lines) >= 1:
                    header_fields = lines[0].strip().split(',')
                    field_count = len(header_fields) if header_fields[0] else 0
            
            print(f"  Archivo: {template_path.name}")
            print(f"  Ruta: {template_path}")
            print(f"  Tamaño: {file_size / 1024:.1f} KB")
            print(f"  Campos totales: {field_count}")
            print(f"  Tiempo: {(end_time - start_time).total_seconds():.2f}s")

        else:
            print(f"  ERROR: Archivo no generado")

        print("\n" + "=" * 60)
        print("PROCESO COMPLETADO")
        print("=" * 60)

    except Exception as e:
        print(f"\nERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()