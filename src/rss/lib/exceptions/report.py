class NoCustomCalculatorError(ValueError):
    """Raised when a report with calculated fields is rendered without a defined field calculator."""
    pass
