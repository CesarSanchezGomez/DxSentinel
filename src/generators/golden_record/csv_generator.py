from typing import Dict, List, Optional
import csv
from .element_processor import ElementProcessor
from .language_resolver import GoldenRecordLanguageResolver
from .exceptions import GoldenRecordError


class CSVGenerator:
    """Generates golden_record_template.csv file."""

    def __init__(self, target_country: Optional[str] = None):
        """
        Args:
            target_country: Código de país específico a incluir (ej: "MEX").
                           Si es None, incluye todos los países.
        """
        self.processor = ElementProcessor(target_country=target_country)
        self.language_resolver = GoldenRecordLanguageResolver()
        self.target_country = target_country

    def generate_template_csv(self, parsed_model: Dict, output_path: str,
                              language_code: str) -> str:
        """
        Generates CSV template with translated labels.

        Args:
            parsed_model: Parsed SDM model
            output_path: Output file path
            language_code: Language code for labels

        Returns:
            Path to generated file
        """
        try:
            processed_data = self.processor.process_model(parsed_model)
            elements = processed_data.get("elements", [])
            
            # Estadísticas
            #country_elements = [e for e in elements if e.get("is_country_specific")]
            #global_elements = [e for e in elements if not e.get("is_country_specific")]
            
            #if self.target_country:
            #    print(f"📊 Elementos procesados para {self.target_country}:")
            #    print(f"   - Globales: {len(global_elements)}")
            #    print(f"   - Específicos de {self.target_country}: {len(country_elements)}")
            #else:
            #    print(f"📊 Elementos procesados (todos países):")
            #    print(f"   - Globales: {len(global_elements)}")
            #    print(f"   - Específicos por país: {len(country_elements)}")

            columns = []
            for element in elements:
                for field in element["fields"]:
                    columns.append({
                        "full_id": field["full_field_id"],
                        "field_id": field["field_id"],
                        "node": field["node"],
                        "is_country_specific": field.get("is_country_specific", False),
                        "country_code": field.get("country_code"),
                        "element_id": element["element_id"]
                    })

            translated_labels = self._get_translated_labels(columns, language_code)

            with open(output_path, 'w', newline='', encoding='utf-8-sig') as csvfile:
                writer = csv.writer(csvfile)

                # Header técnico
                technical_header = [col["full_id"] for col in columns]
                writer.writerow(technical_header)

                # Header descriptivo (traducido)
                descriptive_header = [
                    translated_labels.get(col["full_id"], col["field_id"])
                    for col in columns
                ]
                writer.writerow(descriptive_header)

                # Fila vacía para separación
                #writer.writerow([])
                
                # Metadata adicional
                #writer.writerow(["# Metadata de generación:"])
                #writer.writerow([f"# Idioma: {language_code}"])
                #writer.writerow([f"# Elementos globales: {len(global_elements)}"])
                #writer.writerow([f"# Elementos específicos por país: {len(country_elements)}"])
                
                #if self.target_country:
                #    writer.writerow([f"# País filtrado: {self.target_country}"])
                #else:
                #    writer.writerow([f"# Modo: Todos los países incluidos"])
                
                #writer.writerow([f"# Campos totales: {len(columns)}"])
                
                # Estadísticas por país
                #if country_elements:
                #    writer.writerow(["", "# Estadísticas por país:"])
                #    country_stats = {}
                #    for elem in country_elements:
                #        country = elem.get("country_code", "Desconocido")
                #        if country not in country_stats:
                #            country_stats[country] = 0
                #        country_stats[country] += elem.get("field_count", 0)
                    
                #    for country, count in sorted(country_stats.items()):
                #        writer.writerow(["", f"#   {country}: {count} campos"])

            return output_path

        except Exception as e:
            raise GoldenRecordError(f"Error generating template CSV: {str(e)}") from e

    def _get_translated_labels(self, columns: List[Dict], language_code: str) -> Dict[str, str]:
        """Gets translated labels for all columns."""
        labels_dict = {}

        for column in columns:
            field_node = column["node"]
            full_field_id = column["full_id"]

            field_labels = field_node.get("labels", {})
            label, _ = self.language_resolver.resolve_label(field_labels, language_code)

            if not label:
                label = column["field_id"]
                
                # Para campos específicos por país, agregar indicador
                if column.get("is_country_specific"):
                    country = column.get("country_code", "")
                    label = f"{label} ({country})"

            labels_dict[full_field_id] = label

        return labels_dict
