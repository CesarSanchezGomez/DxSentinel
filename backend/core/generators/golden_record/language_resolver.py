from typing import Dict, Tuple


class GoldenRecordLanguageResolver:
    """Resolves labels according to requested language."""

    @staticmethod
    def _normalize_for_comparison(code: str) -> str:
        """Normalizes language code for case-insensitive comparison."""
        return code.lower().replace('_', '-')

    @staticmethod
    def _get_language_base(code: str) -> str:
        """Gets base part of language code."""
        normalized = GoldenRecordLanguageResolver._normalize_for_comparison(code)
        return normalized.split('-')[0]

    @staticmethod
    def resolve_label(labels: Dict[str, str], language_code: str) -> Tuple[str, bool]:
        """
        Resolves a label for a specific language.

        Args:
            labels: Dictionary {language_code: label}
            language_code: Requested language code (e.g., "es-MX")

        Returns:
            Tuple (resolved_label, is_fallback)
        """
        if not labels:
            return "", True

        requested_normalized = GoldenRecordLanguageResolver._normalize_for_comparison(language_code)
        requested_base = GoldenRecordLanguageResolver._get_language_base(language_code)

        for stored_code, label in labels.items():
            stored_normalized = GoldenRecordLanguageResolver._normalize_for_comparison(stored_code)
            if stored_normalized == requested_normalized:
                return label, False

        for stored_code, label in labels.items():
            stored_normalized = GoldenRecordLanguageResolver._normalize_for_comparison(stored_code)
            stored_base = GoldenRecordLanguageResolver._get_language_base(stored_code)

            if stored_base == requested_base:
                return label, True

        if 'default' in labels:
            return labels['default'], True

        if labels:
            return next(iter(labels.values())), True

        return "", True
