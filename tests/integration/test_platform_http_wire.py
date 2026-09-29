from __future__ import annotations

import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from tinlance_agent_os.transport import (
    HttpPlatformTransport,
    PlatformRequestContext,
    StaticAccessTokenProvider,
)


class Handler(BaseHTTPRequestHandler):
    last_headers: dict[str, str] = {}
    last_body: dict[str, object] = {}

    def do_POST(self) -> None:  # noqa: N802
        length = int(self.headers["Content-Length"])
        Handler.last_headers = {key.lower(): value for key, value in self.headers.items()}
        Handler.last_body = json.loads(self.rfile.read(length).decode())
        raw = json.dumps({"status": "ok", "payload": {"ready": True}}).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("X-Tinlance-API-Version", "1.1")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def log_message(self, _format: str, *_args: object) -> None:
        return


def test_platform_http_wire_contract() -> None:
    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        transport = HttpPlatformTransport(
            f"http://127.0.0.1:{server.server_address[1]}/v1/agent-platform",
            StaticAccessTokenProvider("test-token"),
            allow_insecure_localhost=True,
        )
        payload = transport.send(
            operation="health",
            payload={},
            context=PlatformRequestContext("tenant-a", "subject-a", "request-a"),
            idempotent=True,
        )
        assert payload == {"ready": True}
        assert Handler.last_headers["authorization"] == "Bearer test-token"
        assert Handler.last_headers["x-tinlance-api-version"] == "1.1"
        assert Handler.last_headers["x-tinlance-tenant-id"] == "tenant-a"
        assert Handler.last_headers["x-tinlance-subject-id"] == "subject-a"
        assert Handler.last_headers["x-request-id"] == "request-a"
        assert Handler.last_headers["idempotency-key"] == "request-a"
        assert Handler.last_body == {
            "operation": "health",
            "tenant_id": "tenant-a",
            "subject_id": "subject-a",
            "payload": {},
        }
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)