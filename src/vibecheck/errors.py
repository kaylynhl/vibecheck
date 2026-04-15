"""Custom exceptions for the vibecheck backend pipeline."""


class VibecheckError(Exception):
    """Base exception for all pipeline-related errors."""


class ConfigurationError(VibecheckError):
    """Raised when required runtime configuration is missing or invalid."""


class InputNormalizationError(VibecheckError):
    """Raised when image inputs cannot be normalized for processing."""


class VisionAPIError(VibecheckError):
    """Raised when the Groq vision API request fails or returns unusable data."""


class TagExtractionError(VibecheckError):
    """Raised when structured tags cannot be extracted from the description."""
