"""Errors raised at the Agent Platform integration boundary."""


class PlatformAdapterError(RuntimeError):
    """Base error for failures crossing the Agent Platform boundary."""


class PlatformTransportError(PlatformAdapterError):
    """The transport could not complete a request."""


class PlatformAuthenticationError(PlatformAdapterError):
    """The Platform rejected the supplied authentication."""


class PlatformAuthorizationError(PlatformAdapterError):
    """The Platform rejected the caller's authority."""


class PlatformProtocolError(PlatformAdapterError):
    """The remote response violated the agreed wire contract."""


class PlatformVersionError(PlatformProtocolError):
    """The remote Platform does not support the required API version."""


class PlatformUnavailableError(PlatformTransportError):
    """The Platform is unavailable after permitted retries."""


class PlatformConflictError(PlatformAdapterError):
    """The Platform rejected a request with a stable conflict classification.

    The error code and retryability are authoritative response metadata, not
    permission to retry or bypass policy. Callers must not infer approval from
    this exception or repeat consequential operations unless idempotency rules
    allow it.
    """

    def __init__(
        self,
        *,
        status_code: int,
        error_code: str,
        retryable: bool,
    ) -> None:
        super().__init__(f"Platform rejected the request: {error_code}")
        if status_code < 400 or status_code > 599:
            raise ValueError("status_code must be an HTTP error status")
        if not error_code or error_code != error_code.strip() or len(error_code) > 128:
            raise ValueError("error_code must be normalized and bounded")
        if not isinstance(retryable, bool):
            raise TypeError("retryable must be a boolean")
        self.status_code = status_code
        self.error_code = error_code
        self.retryable = retryable
