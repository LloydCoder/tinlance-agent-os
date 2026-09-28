"""Provider-neutral transport for the Agent Platform API contract."""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Protocol
from urllib.parse import urlparse

from .errors import (
    PlatformAuthenticationError,
    PlatformAuthorizationError,
    PlatformProtocolError,
    PlatformTransportError,
    PlatformUnavailableError,
    PlatformVersionError,
)

API_VERSION = "1.1"
MAX_RESPONSE_BYTES = 4 * 1024 * 1024
RETRYABLE_STATUS_CODES = frozenset({429, 502, 503, 504})


@dataclass(frozen=True, slots=True)
class PlatformRequestContext:
    """Caller identity and trace context propagated to one Platform request."""

    tenant_id: str
    subject_id: str
    request_id: str
    trace_id: str | None = None

    def __post_init__(self) -> None:
        values = (
            (self.tenant_id, "tenant_id"),
            (self.subject_id, "subject_id"),
            (self.request_id, "request_id"),
        )
        for value, name in values:
            if not value or value != value.strip():
                raise ValueError(f"{name} must be non-empty and normalized")
        if self.trace_id is not None and (
            not self.trace_id or self.trace_id != self.trace_id.strip()
        ):
            raise ValueError("trace_id must be normalized when provided")

class AccessTokenProvider(Protocol):
    def token(self) -> str: ...


@dataclass(frozen=True, slots=True)
class StaticAccessTokenProvider:
    """Simple provider for service-to-service tokens supplied by the caller."""

    access_token: str = field(repr=False)

    def __post_init__(self) -> None:
        if (
            not self.access_token
            or self.access_token != self.access_token.strip()
            or any(character.isspace() for character in self.access_token)
            or any(character in self.access_token for character in "\r\n")
        ):
            raise ValueError("access token must be a non-empty bearer token")

    def token(self) -> str:
        return self.access_token

class PlatformTransport(Protocol):
    def send(
        self,
        *,
        operation: str,
        payload: Mapping[str, object],
        context: PlatformRequestContext,
        idempotent: bool,
    ) -> Mapping[str, object]: ...


@dataclass(frozen=True, slots=True)
class HttpPlatformTransport:
    """HTTPS transport for the Platform APIRequest/APIResponse boundary."""

    endpoint: str
    token_provider: AccessTokenProvider
    timeout_seconds: float = 10.0
    max_retries: int = 2
    retry_backoff_seconds: float = 0.25
    allow_insecure_localhost: bool = False

    def __post_init__(self) -> None:
        parsed = urlparse(self.endpoint)
        if parsed.scheme not in {'https', 'http'} or not parsed.netloc:
            raise ValueError("endpoint must be an absolute HTTP(S) URL")
        if parsed.username is not None or parsed.password is not None:
            raise ValueError("endpoint must not contain embedded credentials")
        if parsed.scheme == 'http' and not (
            self.allow_insecure_localhost
            and parsed.hostname in {'127.0.0.1', '::1', 'localhost'}
        ):
            raise ValueError("HTTPS is required unless insecure localhost is explicitly enabled")
        if self.timeout_seconds <= 0 or self.max_retries < 0 or self.retry_backoff_seconds < 0:
            raise ValueError("transport limits must be valid")

    def send(
        self,
        *,
        operation: str,
        payload: Mapping[str, object],
        context: PlatformRequestContext,
        idempotent: bool,
    ) -> Mapping[str, object]:
        if not operation or operation != operation.strip():
            raise ValueError("operation must be normalized")
        token = self.token_provider.token()
        if not token or token != token.strip() or any(character.isspace() for character in token):
            raise PlatformAuthenticationError("access token provider returned an invalid token")
        body = json.dumps(
            {
                'api_version': API_VERSION,
                'operation': operation,
                'tenant_id': context.tenant_id,
                'subject_id': context.subject_id,
                'request_id': context.request_id,
                'payload': dict(payload),
            },
            separators=(',', ':'),
        ).encode("utf-8")
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}",
            "X-Tinlance-API-Version": API_VERSION,
            "X-Tinlance-Tenant-ID": context.tenant_id,
            "X-Tinlance-Subject-ID": context.subject_id,
            "X-Request-ID": context.request_id,
        }
        if context.trace_id:
            headers["traceparent"] = context.trace_id
        attempts = 1 + (self.max_retries if idempotent else 0)
        last_error: PlatformTransportError | None = None
        for attempt in range(attempts):
            try:
                return self._send_once(body, headers)
            except _RetryableResponse as exc:
                last_error = exc
                if attempt + 1 >= attempts:
                    break
                time.sleep(self.retry_backoff_seconds * (2**attempt))
        if last_error is not None:
            if isinstance(last_error, _RetryableResponse):
                raise PlatformUnavailableError(
                    'Platform remained unavailable after permitted retries'
                ) from last_error
            raise last_error
        raise PlatformUnavailableError("Platform request failed")

    def _send_once(self, body: bytes, headers: Mapping[str, str]) -> Mapping[str, object]:
        request = urllib.request.Request(
            self.endpoint,
            data=body,
            headers=dict(headers),
            method="POST",
        )
        try:
            opener = urllib.request.build_opener(_NoRedirectHandler())
            with opener.open(request, timeout=self.timeout_seconds) as response:
                raw = response.read(MAX_RESPONSE_BYTES + 1)
                status = getattr(response, 'status', 200)
                response_headers = getattr(response, 'headers', {})
        except urllib.error.HTTPError as exc:
            if exc.code in RETRYABLE_STATUS_CODES:
                raise _RetryableResponse(exc.code) from exc
            if exc.code == 401:
                raise PlatformAuthenticationError("Platform authentication failed") from exc
            if exc.code == 403:
                raise PlatformAuthorizationError("Platform authorization failed") from exc
            if exc.code == 426:
                raise PlatformVersionError("Platform requires a different API version") from exc
            raise PlatformTransportError(f"Platform returned HTTP {exc.code}") from exc
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            raise PlatformTransportError("Platform transport failed") from exc
        if status in RETRYABLE_STATUS_CODES:
            raise _RetryableResponse(status)
        if status == 401:
            raise PlatformAuthenticationError("Platform authentication failed")
        if status == 403:
            raise PlatformAuthorizationError("Platform authorization failed")
        if status == 426:
            raise PlatformVersionError("Platform requires a different API version")
        if status < 200 or status >= 300:
            raise PlatformTransportError(f"Platform returned HTTP {status}")
        if len(raw) > MAX_RESPONSE_BYTES:
            raise PlatformProtocolError("Platform response exceeds the maximum permitted size")
        content_type = str(response_headers.get('Content-Type', ''))
        if "json" not in content_type.lower():
            raise PlatformProtocolError("Platform response must be JSON")
        try:
            decoded = json.loads(raw.decode('utf-8'))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise PlatformProtocolError("Platform response is not valid UTF-8 JSON") from exc
        if not isinstance(decoded, dict):
            raise PlatformProtocolError("Platform response must be a JSON object")
        if decoded.get('api_version') != API_VERSION:
            raise PlatformVersionError("Platform response API version is incompatible")
        if decoded.get("status") not in {"ok", "accepted"}:
            raise PlatformProtocolError("Platform response status is invalid")
        payload = decoded.get("payload")
        if not isinstance(payload, dict):
            raise PlatformProtocolError("Platform response payload must be an object")
        return payload

class _NoRedirectHandler(urllib.request.HTTPRedirectHandler):
    def redirect_request(
        self,
        req: urllib.request.Request,
        fp: object,
        code: int,
        msg: str,
        headers: Mapping[str, str],
        newurl: str,
    ) -> urllib.request.Request | None:
        raise PlatformTransportError("Platform endpoint redirects are not permitted")

class _RetryableResponse(PlatformTransportError):
    def __init__(self, status: int) -> None:
        super().__init__(f"retryable Platform response: HTTP {status}")