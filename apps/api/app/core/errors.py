class ForgeError(Exception):
    """Base error for FORGE system."""
    pass


class ProviderError(ForgeError):
    """Base error for LLM provider operations."""
    pass


class ProviderTimeoutError(ProviderError):
    """Raised when provider call times out."""
    pass


class ProviderRateLimitError(ProviderError):
    """Raised when rate limit is exceeded."""
    pass


class ProviderAuthenticationError(ProviderError):
    """Raised when API key or authentication fails."""
    pass


class ProviderInvalidRequestError(ProviderError):
    """Raised when request parameters or schema are invalid."""
    pass


class ProviderResponseFormatError(ProviderError):
    """Raised when model returns malformed or invalid output."""
    pass


# Backward compatibility alias
ProviderInvalidResponseError = ProviderResponseFormatError


class ToolExecutionError(ForgeError):
    """Raised when a tool encounters an unhandled execution error."""
    pass


class VerificationError(ForgeError):
    """Raised when verification constraints fail."""
    pass


class ProvenanceIntegrityError(ForgeError):
    """Raised when event hash chain verification fails."""
    pass
