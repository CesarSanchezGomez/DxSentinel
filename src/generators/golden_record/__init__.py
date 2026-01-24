from typing import Dict, Optional
from pathlib import Path
from .csv_generator import CSVGenerator
from .exceptions import GoldenRecordError

__version__ = "1.0.0"
__all__ = ["GoldenRecordGenerator", "GoldenRecordError"]


class GoldenRecordGenerator:
    """Generator for golden_record_template.csv only."""

    def __init__(self, output_dir: str = "output/golden_record", target_country: Optional[str] = None):
        """
        Args:
            output_dir: Directorio de salida para los archivos CSV
            target_country: Código de país específico a incluir (ej: "MEX").
                           Si es None, incluye todos los países.
        """
        self.output_dir = output_dir
        self.target_country = target_country
        self.csv_gen = CSVGenerator(target_country=target_country)

    def generate_template(self, parsed_model: Dict, language_code: str = "en") -> str:
        """
        Generates golden_record_template.csv file.

        Args:
            parsed_model: Parsed SDM model
            language_code: Language code for labels

        Returns:
            Path to generated template file
        """
        try:
            output_dir = Path(self.output_dir)
            output_dir.mkdir(parents=True, exist_ok=True)

            language_normalized = language_code.lower().replace('_', '-')
            
            # Nombre de archivo basado en país si está filtrado
            if self.target_country:
                template_name = f"golden_record_template_{language_normalized}_{self.target_country}.csv"
            else:
                template_name = f"golden_record_template_{language_normalized}.csv"
            
            template_path = output_dir / template_name

            if self.target_country:
                print(f"🎯 Generando golden record para país: {self.target_country}")
                print(f"📄 Archivo: {template_name}")
            
            return self.csv_gen.generate_template_csv(
                parsed_model, str(template_path), language_normalized
            )

        except Exception as e:
            raise GoldenRecordError(f"Error generating template: {str(e)}") from e