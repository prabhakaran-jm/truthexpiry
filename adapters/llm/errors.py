class LlmExtractionError(Exception):
    """Base class for live extraction adapter failures."""


class QueryTooLongError(LlmExtractionError):
    """User query exceeds the configured character limit."""


class ProviderTimeoutError(LlmExtractionError):
    """Provider call exceeded the fixed timeout."""


class ProviderTransportError(LlmExtractionError):
    """Provider transport or API failure."""


class MalformedStructuredOutputError(LlmExtractionError):
    """Structured output failed validation."""


class UnknownEvidenceIdError(LlmExtractionError):
    """Model returned an evidence ID not present in the request-local map."""


class DuplicateEvidenceIdError(LlmExtractionError):
    """Model returned duplicate evidence IDs."""


class EmptyEvidenceIdsError(LlmExtractionError):
    """Non-null claim returned without evidence IDs."""


class UnsupportedClaimSchemaError(LlmExtractionError):
    """Entity/attribute pair is not in the domain catalog."""


class InvalidScopeError(LlmExtractionError):
    """Scope keys or values failed catalog validation."""


class ScopeKeyCollisionError(InvalidScopeError):
    """Distinct scope keys normalized to the same canonical key."""


class InvalidStatedValueError(LlmExtractionError):
    """Stated value is not allowed for the catalog entry."""
