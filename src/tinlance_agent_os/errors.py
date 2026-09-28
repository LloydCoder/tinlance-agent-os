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
