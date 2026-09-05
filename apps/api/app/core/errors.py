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


class ProviderInvalidResponseError(ProviderError):
    """Raised when model returns malformed or invalid output."""
    pass


class ToolExecutionError(ForgeError):
    """Raised when a tool encounters an unhandled execution error."""
    pass


class VerificationError(ForgeError):
    """Raised when verification constraints fail."""
    pass


class ProvenanceIntegrityError(ForgeError):
    """Raised when event hash chain verification fails."""
    pass
