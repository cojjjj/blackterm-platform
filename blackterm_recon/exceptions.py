class BlacktermError(Exception):
    """Base application error."""


class TargetValidationError(BlacktermError):
    """Raised when target policy validation fails."""


class PortSpecificationError(BlacktermError):
    """Raised when ports cannot be parsed."""
