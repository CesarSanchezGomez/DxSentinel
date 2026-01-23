from typing import Dict
from pathlib import Path
from .csv_generator import CSVGenerator
from .exceptions import GoldenRecordError

__version__ = "1.0.0"
__all__ = ["GoldenRecordGenerator", "GoldenRecordError"]


class GoldenRecordGenerator:
    """Generator for golden_record_template.csv only."""

    def __init__(self, output_dir: str = "output/golden_record"):
        self.output_dir = output_dir
        self.csv_gen = CSVGenerator()

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
            template_path = output_dir / f"golden_record_template_{language_normalized}.csv"

            return self.csv_gen.generate_template_csv(
                parsed_model, str(template_path), language_normalized
            )

        except Exception as e:
            raise GoldenRecordError(f"Error generating template: {str(e)}") from e
