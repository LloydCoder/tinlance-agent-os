from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Thread

import pytest

from tinlance_agent_os.errors import (
    PlatformAuthenticationError,
    PlatformProtocolError,
    PlatformVersionError,
)
from tinlance_agent_os.transport import (
    API_VERSION,
    HttpPlatformTransport,
    PlatformRequestContext,
    StaticAccessTokenProvider,
)


class Handler(BaseHTTPRequestHandler):
    response_status = 200
    response_body = {"status": "ok", "payload": {"ready": True}}
    response_version = API_VERSION
    last_headers: dict[str, str] = {}
    last_body: dict[str, object] = {}

    def do_POST(self) -> None:  # noqa: N802
        length = int(self.headers["Content-Length"])
        Handler.last_headers = {key.lower(): value for key, value in self.headers.items()}
        Handler.last_body = json.loads(self.rfile.read(length))
        self.send_response(Handler.response_status)
        self.send_header("Content-Type", "application/json")
        self.send_header("X-Tinlance-API-Version", Handler.response_version)
        encoded = json.dumps(Handler.response_body).encode()
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

    def log_message(self, format: str, *args: object) -> None:
        return


@pytest.fixture
def server():
    Handler.response_status = 200
    Handler.response_version = API_VERSION
    Handler.response_body = {"status": "ok", "payload": {"ready": True}}
    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}"
    finally:
        server.shutdown()
        thread.join(timeout=2)


def context() -> PlatformRequestContext:
    return PlatformRequestContext("tenant-1", "subject-1", "trace-1")


def test_https_is_required_by_default() -> None:
    with pytest.raises(ValueError):
        HttpPlatformTransport("http://example.com", StaticAccessTokenProvider("token"))


@pytest.mark.parametrize("timeout_seconds", [0, -1, float("nan"), float("inf"), -float("inf")])
def test_transport_rejects_non_finite_or_non_positive_timeouts(timeout_seconds: float) -> None:
    with pytest.raises(ValueError, match="transport limits must be finite and valid"):
        HttpPlatformTransport(
            "https://platform.example",
            StaticAccessTokenProvider("token"),
            timeout_seconds=timeout_seconds,
        )


@pytest.mark.parametrize("retry_backoff_seconds", [-1, float("nan"), float("inf"), -float("inf")])
def test_transport_rejects_invalid_retry_backoff(retry_backoff_seconds: float) -> None:
    with pytest.raises(ValueError, match="transport limits must be finite and valid"):
        HttpPlatformTransport(
            "https://platform.example",
            StaticAccessTokenProvider("token"),
            retry_backoff_seconds=retry_backoff_seconds,
        )


@pytest.mark.parametrize("max_retries", [-1, True, 1.5])
def test_transport_rejects_invalid_retry_count(max_retries: int) -> None:
    with pytest.raises(ValueError, match="transport limits must be finite and valid"):
        HttpPlatformTransport(
            "https://platform.example",
            StaticAccessTokenProvider("token"),
            max_retries=max_retries,
        )


def test_transport_propagates_authenticated_context(server) -> None:
    transport = HttpPlatformTransport(
        server, StaticAccessTokenProvider("secret"), allow_insecure_localhost=True
    )
    payload = transport.send(operation="health", payload={}, context=context(), idempotent=True)
    assert payload["ready"] is True
    assert Handler.last_headers["authorization"] == "Bearer secret"
    assert Handler.last_headers["x-tinlance-tenant-id"] == "tenant-1"
    assert "traceparent" not in Handler.last_headers
    assert "api_version" not in Handler.last_body
    assert Handler.last_body["subject_id"] == "subject-1"


def test_authentication_and_version_fail_closed(server) -> None:
    Handler.response_status = 401
    with pytest.raises(PlatformAuthenticationError):
        HttpPlatformTransport(
            server, StaticAccessTokenProvider("secret"), allow_insecure_localhost=True
        ).send(operation="health", payload={}, context=context(), idempotent=True)

    Handler.response_status = 200
    Handler.response_status = 200
    Handler.response_version = "999"
    Handler.response_body = {"status": "ok", "payload": {}}
    with pytest.raises(PlatformVersionError):
        HttpPlatformTransport(
            server, StaticAccessTokenProvider("secret"), allow_insecure_localhost=True
        ).send(operation="health", payload={}, context=context(), idempotent=True)


def test_non_json_fails_closed(server) -> None:
    Handler.response_version = API_VERSION
    Handler.response_body = {"status": "ok", "payload": []}
    with pytest.raises(PlatformProtocolError):
        HttpPlatformTransport(
            server, StaticAccessTokenProvider("secret"), allow_insecure_localhost=True
        ).send(operation="health", payload={}, context=context(), idempotent=True)


def test_transport_propagates_only_valid_w3c_traceparent(server) -> None:
    trace_id = "4bf92f3577b34da6a3ce929d0e0e4736"
    traceparent = f"00-{trace_id}-00f067aa0ba902b7-01"
    transport = HttpPlatformTransport(
        server, StaticAccessTokenProvider("secret"), allow_insecure_localhost=True
    )
    transport.send(
        operation="health",
        payload={},
        context=PlatformRequestContext(
            "tenant-1", "subject-1", "request-1", trace_id=trace_id, traceparent=traceparent
        ),
        idempotent=True,
    )
    assert Handler.last_headers["traceparent"] == traceparent


def test_transport_rejects_invalid_traceparent(server) -> None:
    with pytest.raises(ValueError, match="traceparent"):
        PlatformRequestContext(
            "tenant-1",
            "subject-1",
            "request-1",
            traceparent=f"00-{'0' * 32}-00f067aa0ba902b7-01",
        )
