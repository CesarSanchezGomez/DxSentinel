class GoldenRecordError(Exception):
    """Base exception for Golden Record generation errors."""
    pass


class ElementNotFoundError(GoldenRecordError):
    """Error when expected elements are not found."""
    pass


class FieldFilterError(GoldenRecordError):
    """Error in field filtering."""
    pass
