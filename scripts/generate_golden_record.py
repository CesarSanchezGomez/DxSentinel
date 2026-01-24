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


def debug_print_structure(node: dict, level: int = 0, max_depth: int = 3, print_all: bool = False):
    """Función de debug para imprimir la estructura del árbol XML."""
    indent = "  " * level
    
    if level > max_depth:
        if print_all:
            print(f"{indent}... (profundidad máxima: {max_depth})")
        return
    
    tag = node.get("tag", "")
    elem_id = node.get("technical_id") or node.get("id", "")
    attributes = node.get("attributes", {}).get("raw", {})
    data_origin = attributes.get("data-origin", "")
    data_country = attributes.get("data-country", "")
    
    # Solo imprimir elementos relevantes para el análisis
    if print_all or tag in ["hris-element", "country", "XMLDocument"] or data_origin:
        origin_info = f" [origin={data_origin}]" if data_origin else ""
        country_info = f" [country={data_country}]" if data_country else ""
        print(f"{indent}├─ {tag}: {elem_id}{origin_info}{country_info}")
    
    # Continuar con los hijos
    for child in node.get("children", []):
        debug_print_structure(child, level + 1, max_depth, print_all)


def print_parsed_model_summary(parsed_model: dict):
    """Imprime un resumen del modelo parseado."""
    structure = parsed_model.get("structure", {})
    
    print("\n🔍 RESUMEN DEL MODELO PARSEADO:")
    print("-" * 40)
    
    # Contar elementos
    def count_elements(node: dict, counts: dict):
        tag = node.get("tag", "")
        if tag:
            if tag not in counts:
                counts[tag] = 0
            counts[tag] += 1
        
        for child in node.get("children", []):
            count_elements(child, counts)
    
    counts = {}
    count_elements(structure, counts)
    
    for tag, count in sorted(counts.items()):
        print(f"  {tag}: {count}")
    
    # Elementos con data-origin
    def find_elements_with_origin(node: dict, results: list):
        attributes = node.get("attributes", {}).get("raw", {})
        origin = attributes.get("data-origin")
        if origin:
            results.append({
                "tag": node.get("tag", ""),
                "id": node.get("technical_id") or node.get("id", ""),
                "origin": origin,
                "country": attributes.get("data-country", "")
            })
        
        for child in node.get("children", []):
            find_elements_with_origin(child, results)
    
    origins = []
    find_elements_with_origin(structure, origins)
    
    if origins:
        print("\n  🎯 ELEMENTOS CON DATA-ORIGIN:")
        for item in origins:
            country_info = f" (country={item['country']})" if item['country'] else ""
            print(f"    • {item['tag']}: {item['id']} [origin={item['origin']}]{country_info}")
    
    # Países encontrados
    def find_countries(node: dict, countries: set):
        if node.get("tag", "").lower() == "country":
            country_code = node.get("technical_id") or node.get("id", "")
            if country_code:
                countries.add(country_code)
        
        for child in node.get("children", []):
            find_countries(child, countries)
    
    countries = set()
    find_countries(structure, countries)
    
    if countries:
        print(f"\n  🌍 PAÍSES ENCONTRADOS: {', '.join(sorted(countries))}")


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
            print(f"❌ ERROR: Archivo principal no encontrado")
            print(f"   Ruta: {MAIN_XML_FILE.absolute()}")
            
            data_dir = get_absolute_path("data")
            if data_dir.exists():
                print(f"\n📁 Archivos XML en {data_dir}:")
                for file in data_dir.rglob("*.xml"):
                    print(f"   - {file.relative_to(data_dir)}")
            
            return

        print(f"   ✅ Archivo principal: {MAIN_XML_FILE.name}")
        
        # Verificar archivo CSF (opcional)
        use_csf = True
        if not CSF_XML_FILE.exists():
            print(f"   ⚠️  Archivo CSF no encontrado: {CSF_XML_FILE.name}")
            print(f"   ℹ️  Continuando solo con archivo principal")
            use_csf = False
        else:
            print(f"   ✅ Archivo CSF: {CSF_XML_FILE.name}")

        # 2. Parsear XML
        print(f"\n2. Parseando SDM...")
        try:
            if use_csf:
                print(f"   Fusionando con CSF...")
                parsed_model = parse_successfactors_with_csf(
                    str(MAIN_XML_FILE), 
                    str(CSF_XML_FILE)
                )
            else:
                # Usar solo el archivo principal
                from parsing.xml_loader import XMLLoader
                from parsing.xml_parser import XMLParser
                from parsing.xml_normalizer import XMLNormalizer
                
                loader = XMLLoader()
                parser = XMLParser()
                normalizer = XMLNormalizer()
                
                root = loader.load_from_file(str(MAIN_XML_FILE), "golden_record")
                document = parser.parse_document(root, "golden_record")
                parsed_model = normalizer.normalize_document(document)
            
            print("   ✅ SDM parseado correctamente")
            
            # Mostrar resumen del modelo parseado
            print_parsed_model_summary(parsed_model)
            
            # DEBUG: Mostrar estructura detallada (opcional - descomentar si es necesario)
            # print(f"\n   🔍 Estructura detallada (primeros 3 niveles):")
            # structure = parsed_model.get("structure", {})
            # debug_print_structure(structure, max_depth=3, print_all=True)
            
        except Exception as parse_error:
            print(f"   ❌ Error parseando XML: {parse_error}")
            raise

        # 3. Generar template
        print(f"\n3. Generando template CSV")
        print(f"   Directorio: {OUTPUT_DIR}")
        print(f"   Idioma: {LANGUAGE_CODE}")
        if COUNTRY_CODE:
            print(f"   País: {COUNTRY_CODE}")

        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        
        # Pasar el código de país al generador
        # IMPORTANTE: Convertir string vacío a None para procesamiento correcto
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
            
            # Leer estadísticas del archivo
            with open(template_path, 'r', encoding='utf-8-sig') as f:
                lines = f.readlines()
                if lines and len(lines) >= 1:
                    header_fields = lines[0].strip().split(',')
                    field_count = len(header_fields) if header_fields[0] else 0
            
            print(f"   📄 Archivo: {template_path.name}")
            print(f"   📁 Ruta: {template_path}")
            print(f"   📊 Tamaño: {file_size / 1024:.1f} KB")
            print(f"   🔢 Campos totales: {field_count}")
            print(f"   ⏱️  Tiempo: {(end_time - start_time).total_seconds():.2f}s")
            
            # Mostrar algunos campos específicos si hay filtro por país
            if COUNTRY_CODE and field_count > 0:
                print(f"\n   🎯 Campos específicos de {COUNTRY_CODE}:")
                country_fields = [f for f in header_fields if COUNTRY_CODE in f]
                if country_fields:
                    print(f"     • Total: {len(country_fields)} campos")
                    for i, field in enumerate(country_fields[:5]):  # Mostrar primeros 5
                        print(f"       - {field}")
                    if len(country_fields) > 5:
                        print(f"       ... y {len(country_fields) - 5} más")
                else:
                    print(f"     ℹ️  No se encontraron campos específicos de {COUNTRY_CODE}")
            
            # Mostrar campos SDM globales
            if field_count > 0:
                print(f"\n   🌍 Campos SDM globales:")
                sdm_fields = [f for f in header_fields if COUNTRY_CODE not in f] if COUNTRY_CODE else header_fields
                global_fields = [f for f in sdm_fields if not any(c in f for c in ["_csf", "CSF"])]
                if global_fields:
                    print(f"     • Total: {len(global_fields)} campos")
                    for i, field in enumerate(global_fields[:5]):  # Mostrar primeros 5
                        print(f"       - {field}")
                    if len(global_fields) > 5:
                        print(f"       ... y {len(global_fields) - 5} más")
                
                # Mostrar campos CSF si existen
                csf_fields = [f for f in header_fields if "_csf" in f or "CSF" in f]
                if csf_fields:
                    print(f"\n   🔧 Campos CSF:")
                    print(f"     • Total: {len(csf_fields)} campos")
                    for i, field in enumerate(csf_fields[:3]):  # Mostrar primeros 3
                        print(f"       - {field}")
                    if len(csf_fields) > 3:
                        print(f"       ... y {len(csf_fields) - 3} más")
        else:
            print(f"   ❌ ERROR: Archivo no generado")

        print("\n" + "=" * 60)
        print("PROCESO COMPLETADO")
        print(f"   Idioma: {LANGUAGE_CODE}")
        if COUNTRY_CODE:
            print(f"   País: {COUNTRY_CODE}")
        else:
            print(f"   País: Todos")
        print("=" * 60)

    except Exception as e:
        print(f"\n❌ ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    # Ejecutar generación principal
    main()