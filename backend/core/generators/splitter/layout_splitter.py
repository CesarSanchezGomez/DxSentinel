from typing import Dict, List, Optional, Tuple
import csv
import json
from pathlib import Path
from backend.core.generators.golden_record.exceptions import GoldenRecordError


class LayoutSplitter:
    """Splits Golden Record CSV into individual SAP layout templates."""

    def __init__(self, metadata_path: str):
        self.metadata = self._load_metadata(metadata_path)
        self.business_keys = self.metadata.get("business_keys", {})
        self.layout_config = self.metadata.get("layout_split_config", {})
        self.field_catalog = self.metadata.get("field_catalog", {})

    def _load_metadata(self, metadata_path: str) -> Dict:
        """Loads metadata JSON file."""
        try:
            with open(metadata_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            raise GoldenRecordError(f"Error loading metadata: {str(e)}") from e

    def split_golden_record(self, golden_record_path: str, output_dir: str) -> List[str]:
        """Splits Golden Record into individual layout CSVs."""
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        golden_data = self._read_golden_record(golden_record_path)
        generated_files = []

        for element_id, config in self.layout_config.items():
            layout_file = self._generate_layout(
                element_id=element_id,
                config=config,
                golden_data=golden_data,
                output_dir=output_path
            )
            if layout_file:
                generated_files.append(layout_file)

        return generated_files

    def _read_golden_record(self, csv_path: str) -> Dict:
        """Reads Golden Record CSV with headers, trying multiple encodings."""
        encodings_to_try = ['utf-8-sig', 'utf-8', 'latin-1', 'cp1252']

        for encoding in encodings_to_try:
            try:
                with open(csv_path, 'r', encoding=encoding) as f:
                    reader = csv.reader(f)
                    technical_header = next(reader)
                    descriptive_header = next(reader)
                    data_rows = list(reader)

                return {
                    "technical_header": technical_header,
                    "descriptive_header": descriptive_header,
                    "data_rows": data_rows
                }
            except (UnicodeDecodeError, UnicodeError):
                continue
            except StopIteration:
                raise GoldenRecordError("CSV file is empty or has insufficient rows")
            except Exception as e:
                raise GoldenRecordError(f"Error reading Golden Record with {encoding}: {str(e)}") from e

        raise GoldenRecordError(
            f"Unable to read file '{csv_path}' with any supported encoding. "
            f"Tried: {', '.join(encodings_to_try)}"
        )

    def _generate_layout(self, element_id: str, config: Dict,
                         golden_data: Dict, output_dir: Path) -> str:
        """Generates individual layout CSV file with SAP business keys."""

        element_fields = config["fields"]
        business_key_config = self.business_keys.get(element_id, {})
        business_keys_list = business_key_config.get("business_keys", [])

        # Estructuras para construir el CSV
        columns = []  # Lista de (sap_column_name, source_index, descriptive_name, is_synthetic)

        # Paso 1: Procesar business keys (pueden ser sintéticas o del Golden Record)
        for bk in business_keys_list:
            golden_column = bk.get("golden_column")
            sap_column = bk.get("sap_column")

            # Intentar encontrar la columna en el Golden Record
            source_info = self._find_source_column(
                golden_column,
                sap_column,
                golden_data["technical_header"]
            )

            if source_info:
                source_idx, descriptive = source_info
                if source_idx < len(golden_data["descriptive_header"]):
                    descriptive = golden_data["descriptive_header"][source_idx]

                columns.append({
                    "sap_name": sap_column,
                    "source_idx": source_idx,
                    "descriptive": descriptive,
                    "is_synthetic": False
                })

        # Paso 2: Agregar campos del elemento (excluyendo los ya agregados)
        added_indices = {col["source_idx"] for col in columns}

        for field_id in element_fields:
            if field_id in golden_data["technical_header"]:
                idx = golden_data["technical_header"].index(field_id)

                if idx not in added_indices:
                    field_name = self._extract_field_name(field_id, element_id)

                    columns.append({
                        "sap_name": field_name,
                        "source_idx": idx,
                        "descriptive": golden_data["descriptive_header"][idx],
                        "is_synthetic": False
                    })
                    added_indices.add(idx)

        if not columns:
            print(f"Warning: No fields found for {element_id}, skipping")
            return None

        # Generar el archivo CSV
        layout_path = output_dir / config["layout_filename"]

        with open(layout_path, 'w', newline='', encoding='utf-8-sig') as f:
            writer = csv.writer(f)

            # Escribir headers
            technical_header = [col["sap_name"] for col in columns]
            descriptive_header = [col["descriptive"] for col in columns]

            writer.writerow(technical_header)
            writer.writerow(descriptive_header)

            # Escribir datos
            for row in golden_data["data_rows"]:
                output_row = []
                for col in columns:
                    idx = col["source_idx"]
                    value = row[idx] if idx < len(row) else ""
                    output_row.append(value)

                writer.writerow(output_row)

        return str(layout_path)

    def _find_source_column(
            self,
            golden_column: Optional[str],
            sap_column: str,
            available_headers: List[str]
    ) -> Optional[Tuple[int, str]]:
        """
        Encuentra la columna fuente en el Golden Record para una business key.

        Lógica de derivación:
        - user-id → personInfo_person-id-external
        - person-id-external → personInfo_person-id-external
        - personInfo.person-id-external → personInfo_person-id-external
        - start-date → {element}_start-date (busca en el elemento actual)
        """

        # Caso 1: La columna está explícitamente mapeada y existe
        if golden_column and golden_column in available_headers:
            idx = available_headers.index(golden_column)
            return (idx, self._generate_descriptive_name(sap_column))

        # Caso 2: Derivar la columna basándose en el nombre SAP
        derived_column = self._derive_golden_column(sap_column, available_headers)

        if derived_column and derived_column in available_headers:
            idx = available_headers.index(derived_column)
            return (idx, self._generate_descriptive_name(sap_column))

        # No se pudo encontrar ni derivar la columna
        return None

    def _derive_golden_column(self, sap_column: str, available_headers: List[str]) -> Optional[str]:
        """
        Deriva la columna del Golden Record basándose en el nombre SAP.

        Reglas de derivación:
        1. user-id → personInfo_person-id-external
        2. person-id-external → personInfo_person-id-external
        3. personInfo.person-id-external → personInfo_person-id-external
        4. start-date → buscar *_start-date en available_headers
        5. Otros campos con referencia (ej: related-person-id-external) → buscar personRelationshipInfo_related-person-id-external
        """

        # Regla 1 y 2: user-id o person-id-external sin prefijo
        if sap_column in ["user-id", "person-id-external"]:
            if "personInfo_person-id-external" in available_headers:
                return "personInfo_person-id-external"

        # Regla 3: Referencias con punto (personInfo.person-id-external)
        if "." in sap_column:
            ref_element, ref_field = sap_column.split(".", 1)
            # Convertir el formato SAP a formato Golden Record
            golden_field = self._sap_to_golden_field(ref_field)
            candidate = f"{ref_element}_{golden_field}"

            if candidate in available_headers:
                return candidate

        # Regla 4: Campos comunes que pueden estar en múltiples elementos
        if sap_column in ["start-date", "end-date", "country", "seq-number"]:
            # Buscar en todos los headers disponibles que terminen con este campo
            golden_field = self._sap_to_golden_field(sap_column)

            for header in available_headers:
                if header.endswith(f"_{golden_field}") or header.endswith(f"-{sap_column}"):
                    return header

        # Regla 5: Buscar coincidencia directa convirtiendo SAP a formato Golden
        golden_field = self._sap_to_golden_field(sap_column)

        # Intentar encontrar en cualquier elemento
        for header in available_headers:
            if header.endswith(f"_{golden_field}"):
                return header

        return None

    def _sap_to_golden_field(self, sap_field: str) -> str:
        """Convierte un campo SAP (kebab-case) a formato Golden Record (kebab-case sin cambios)."""
        # En el Golden Record los campos también usan kebab-case
        return sap_field

    def _generate_descriptive_name(self, sap_column: str) -> str:
        """Genera un nombre descriptivo para una columna SAP."""
        descriptive_map = {
            "user-id": "User ID",
            "person-id-external": "Person ID External",
            "personInfo.person-id-external": "Person ID External",
            "start-date": "Start Date",
            "end-date": "End Date",
            "seq-number": "Sequence Number",
            "pay-component": "Pay Component",
            "email-address": "Email Address",
            "phone-type": "Phone Type",
            "card-type": "Card Type",
            "address-type": "Address Type",
            "country": "Country",
            "relationship": "Relationship",
            "name": "Name",
            "domain": "Domain"
        }

        return descriptive_map.get(sap_column, sap_column.replace("-", " ").title())

    def _extract_field_name(self, full_field_id: str, element_id: str) -> str:
        """Extrae el nombre del campo y lo convierte al formato SAP (kebab-case)."""
        # Remover el prefijo del elemento
        if full_field_id.startswith(f"{element_id}_"):
            field_name = full_field_id[len(element_id) + 1:]
        else:
            field_name = full_field_id

        # En este caso, el Golden Record ya usa kebab-case, así que no necesitamos conversión
        return field_name

    def _camel_to_kebab(self, camel_str: str) -> str:
        """Convierte camelCase a kebab-case."""
        import re
        kebab = re.sub('([a-z0-9])([A-Z])', r'\1-\2', camel_str)
        return kebab.lower()