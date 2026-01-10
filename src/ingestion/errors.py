"""Custom exceptions for data ingestion operations."""


class IngestionError(Exception):
    """Base exception for all ingestion operations."""

    pass


class TransientError(IngestionError):
    """Errors that may succeed on retry.

    Examples:
    - Network timeouts
    - Connection errors
    - HTTP 429 (rate limit)
    - HTTP 5xx (server errors)
    """

    pass


class PermanentError(IngestionError):
    """Errors unlikely to succeed on retry.

    Examples:
    - HTTP 401/403 (authentication/authorization)
    - HTTP 404 (resource not found)
    - Data validation errors
    - Invalid configuration
    """

    pass


class DataQualityError(PermanentError):
    """Data quality issues that require investigation."""

    pass
