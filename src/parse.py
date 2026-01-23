# parse_sample_sdm_fixed.py
"""
Script corregido para parsear XML basado en la estructura real del output.
"""
import sys
from pathlib import Path
import json

# Agregar src al path
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

try:
    from parsing import parse_successfactors_xml
    HAS_PARSER = True
except ImportError as e:
    print(f"⚠️  Error importando parser: {e}")
    HAS_PARSER = False

def main():
    """Parsear sample_sdm.xml y mostrar estructura."""
    
    if not HAS_PARSER:
        print("❌ No se pudo importar el módulo de parsing")
        print("   Verifica que estés en el directorio correcto:")
        print(f"   Directorio actual: {Path.cwd()}")
        return
    
    # Ruta al XML
    xml_path = Path("data/xml/sdm_español.xml")
    
    if not xml_path.exists():
        print(f"❌ Archivo no encontrado: {xml_path}")
        print(f"   Directorio data/xml existe?: {Path('data/xml').exists()}")
        print(f"   Archivos en data/xml/:")
        for f in Path("data/xml").glob("*"):
            print(f"     - {f.name}")
        return
    
    print(f"📂 Parseando: {xml_path}")
    print("=" * 60)
    
    try:
        # 1. Parsear XML - El resultado es un dict según el error
        result = parse_successfactors_xml(
            file_path=str(xml_path),
            source_name="sample_sdm"
        )
        
        print(f"✅ XML parseado exitosamente")
        print(f"📦 Tipo de resultado: {type(result)}")
        
        # 2. Verificar estructura del resultado
        if isinstance(result, dict):
            print("\n📊 Estructura del diccionario retornado:")
            for key, value in result.items():
                if key == "structure":
                    print(f"  {key}: dict con {len(value) if isinstance(value, dict) else '?'} keys")
                elif key == "statistics":
                    print(f"  {key}: {value}")
                elif key == "metadata":
                    print(f"  {key}: dict con {len(value) if isinstance(value, dict) else '?'} keys")
                else:
                    print(f"  {key}: {type(value).__name__}")
            
            # 3. Buscar personalInfo en la estructura
            print("\n🔍 Buscando personalInfo en la estructura...")
            
            def find_in_structure(data, path=""):
                """Busca recursivamente en la estructura."""
                found = []
                
                if isinstance(data, dict):
                    # Buscar por technical_id o id
                    if "technical_id" in data and data["technical_id"]:
                        node_id = str(data["technical_id"]).lower()
                        if "personalinfo" in node_id:
                            found.append((path, data))
                    
                    # Buscar en children
                    if "children" in data and isinstance(data["children"], list):
                        for i, child in enumerate(data["children"]):
                            child_path = f"{path}.children[{i}]"
                            found.extend(find_in_structure(child, child_path))
                    
                    # Buscar en otros campos
                    for key, value in data.items():
                        if key != "children" and isinstance(value, (dict, list)):
                            found.extend(find_in_structure(value, f"{path}.{key}"))
                
                elif isinstance(data, list):
                    for i, item in enumerate(data):
                        found.extend(find_in_structure(item, f"{path}[{i}]"))
                
                return found
            
            # Empezar búsqueda desde structure
            structure = result.get("structure", {})
            personal_info_nodes = find_in_structure(structure, "structure")
            
            if personal_info_nodes:
                print(f"🎯 Encontrados {len(personal_info_nodes)} nodos personalInfo")
                
                for i, (path, node_data) in enumerate(personal_info_nodes[:3]):  # Mostrar máximo 3
                    print(f"\n{'='*50}")
                    print(f"📋 personalInfo #{i+1} (en {path}):")
                    
                    # Información básica del nodo
                    print(f"   Tag: {node_data.get('tag', 'N/A')}")
                    print(f"   ID técnico: {node_data.get('technical_id', 'N/A')}")
                    print(f"   Tipo de nodo: {node_data.get('node_type', 'N/A')}")
                    
                    # Atributos
                    attrs = node_data.get('attributes', {})
                    print(f"   Atributos ({len(attrs)}):")
                    for key, value in list(attrs.items())[:5]:  # Mostrar primeros 5
                        print(f"     {key}: {value}")
                    if len(attrs) > 5:
                        print(f"     ... y {len(attrs) - 5} más")
                    
                    # Labels
                    labels = node_data.get('labels', {})
                    print(f"   Labels ({len(labels)} idiomas):")
                    for lang, text in list(labels.items())[:3]:  # Mostrar primeros 3
                        print(f"     {lang}: {text[:50]}{'...' if len(text) > 50 else ''}")
                    if len(labels) > 3:
                        print(f"     ... y {len(labels) - 3} más")
                    
                    # Children
                    children = node_data.get('children', [])
                    print(f"   Hijos ({len(children)}):")
                    
                    if children:
                        # Mostrar primeros 5 hijos
                        for j, child in enumerate(children[:5]):
                            child_id = child.get('technical_id', child.get('id', f'hijo_{j}'))
                            child_tag = child.get('tag', 'N/A')
                            child_type = child.get('node_type', 'N/A')
                            
                            print(f"     {j+1}. {child_tag} (ID: {child_id}, Tipo: {child_type})")
                            
                            # Mostrar atributos importantes del hijo
                            child_attrs = child.get('attributes', {})
                            important_attrs = {k: v for k, v in child_attrs.items() 
                                            if k in ['type', 'label', 'required', 'max-length']}
                            if important_attrs:
                                print(f"        📋 {important_attrs}")
                        
                        if len(children) > 5:
                            print(f"     ... y {len(children) - 5} más")
                        
                        # Resumen por tipo
                        type_count = {}
                        for child in children:
                            child_type = child.get('node_type', 'unknown')
                            type_count[child_type] = type_count.get(child_type, 0) + 1
                        
                        print(f"\n   📊 Resumen por tipo:")
                        for ttype, count in type_count.items():
                            print(f"     {ttype}: {count}")
                    
                    print(f"{'='*50}")
                
                if len(personal_info_nodes) > 3:
                    print(f"\nℹ️  Mostrando 3 de {len(personal_info_nodes)} personalInfo encontrados")
            
            else:
                print("ℹ️  No se encontró personalInfo con ese nombre exacto")
                
                # Mostrar qué elementos SÍ existen
                print("\n🔍 Mostrando elementos encontrados en el XML:")
                
                def collect_elements(data, elements=None, depth=0, max_depth=3):
                    if elements is None:
                        elements = set()
                    
                    if depth >= max_depth:
                        return elements
                    
                    if isinstance(data, dict):
                        if "technical_id" in data and data["technical_id"]:
                            elements.add(data["technical_id"])
                        
                        if "children" in data and isinstance(data["children"], list):
                            for child in data["children"]:
                                collect_elements(child, elements, depth + 1, max_depth)
                    
                    return elements
                
                unique_elements = collect_elements(structure)
                if unique_elements:
                    print(f"📋 Elementos únicos encontrados ({len(unique_elements)}):")
                    for elem in sorted(list(unique_elements))[:20]:  # Mostrar primeros 20
                        print(f"   • {elem}")
                    if len(unique_elements) > 20:
                        print(f"   ... y {len(unique_elements) - 20} más")
                else:
                    print("   No se encontraron elementos con technical_id")
                    
                    # Intentar otra estrategia: buscar por tag
                    print("\n🔍 Buscando por tags...")
                    tags_found = set()
                    
                    def collect_tags(data, tags=None):
                        if tags is None:
                            tags = set()
                        
                        if isinstance(data, dict):
                            if "tag" in data and data["tag"]:
                                tags.add(data["tag"])
                            
                            if "children" in data and isinstance(data["children"], list):
                                for child in data["children"]:
                                    collect_tags(child, tags)
                        
                        return tags
                    
                    all_tags = collect_tags(structure)
                    if all_tags:
                        print(f"📋 Tags encontrados ({len(all_tags)}):")
                        for tag in sorted(list(all_tags))[:15]:
                            print(f"   • {tag}")
                        if len(all_tags) > 15:
                            print(f"   ... y {len(all_tags) - 15} más")
            
            # 4. Mostrar estadísticas si existen
            stats = result.get("statistics", {})
            if stats:
                print(f"\n📈 Estadísticas del parseo:")
                for key, value in stats.items():
                    if isinstance(value, (int, float, str, bool)):
                        print(f"   {key}: {value}")
                    elif isinstance(value, list):
                        print(f"   {key}: lista con {len(value)} elementos")
                        if key == "unique_tags" and value:
                            print(f"      Ejemplos: {', '.join(value[:5])}")
                    elif isinstance(value, dict):
                        print(f"   {key}: dict con {len(value)} keys")
            
            # 5. Opción: guardar output para análisis
            save_option = input("\n💾 ¿Guardar output completo en JSON? (s/n): ")
            if save_option.lower() == 's':
                output_path = Path("output/parser_output.json")
                output_path.parent.mkdir(parents=True, exist_ok=True)
                
                with open(output_path, 'w', encoding='utf-8') as f:
                    json.dump(result, f, indent=2, ensure_ascii=False)
                
                print(f"✅ Output guardado en: {output_path}")
                print(f"   Tamaño: {output_path.stat().st_size / 1024:.1f} KB")
        
        else:
            print(f"⚠️  Resultado inesperado: {type(result)}")
            print(f"   Valor: {result}")
            
    except Exception as e:
        print(f"\n❌ Error: {type(e).__name__}")
        print(f"   Mensaje: {str(e)}")
        import traceback
        print(f"\n📋 Traceback:")
        traceback.print_exc()

if __name__ == "__main__":
    main()