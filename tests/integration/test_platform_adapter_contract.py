from __future__ import annotations

import contextlib
import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from uuid import uuid4

from tinlance_agent_os.platform_adapter import AgentPlatformAdapter
from tinlance_agent_os.transport import (
    HttpPlatformTransport,
    PlatformRequestContext,
    StaticAccessTokenProvider,
)


class ContractHandler(BaseHTTPRequestHandler):
    calls: list[dict[str, object]] = []

    def do_POST(self) -> None:  # noqa: N802
        length = int(self.headers["Content-Length"])
        body = json.loads(self.rfile.read(length).decode())
        self.calls.append(body)
        operation = body["operation"]
        payload: dict[str, object]
        if operation == "health":
            payload = {"ready": True}
        elif operation == "principal.get":
            payload = {"user_id": "user-a"}
        elif operation == "agents.list":
            payload = {"agents": [{"agent_id": "agent-a", "name": "security", "version": "1.0"}]}
        elif operation == "capabilities.list":
            payload = {"capabilities": [{"capability_id": "repository.read"}]}
        elif operation == "runs.create":
            payload = {"run_id": "run-a", "task_id": body["payload"]["task_id"], "state": "running"}
        elif operation == "approvals.request":
            payload = {"approval_id": "approval-a"}
        elif operation == "runs.events":
            payload = {
                "events": [{
                    "event_id": "event-a",
                    "event_type": "run.created",
                    "occurred_at": "2026-09-29T00:00:00+00:00",
                    "workspace_id": "workspace-a",
                    "correlation_id": "corr-a",
                    "platform_run_id": body["payload"]["run_id"],
                    "payload": {},
                }]
            }
        elif operation == "runs.evidence":
            payload = {"evidence": [{"evidence_id": "evidence-a"}]}
        elif operation == "runs.cancel":
            payload = {
                "run_id": body["payload"]["run_id"],
                "task_id": "task-a",
                "state": "cancelled",
            }
        else:
            self.send_response(400)
            self.end_headers()
            return
        raw = json.dumps({"status": "ok", "payload": payload}).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("X-Tinlance-API-Version", "1.1")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def log_message(self, _format: str, *_args: object) -> None:
        return


def test_adapter_round_trips_against_v11_http_contract() -> None:
    server = ThreadingHTTPServer(("127.0.0.1", 0), ContractHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        transport = HttpPlatformTransport(
            f"http://127.0.0.1:{server.server_address[1]}",
            StaticAccessTokenProvider("test-token"),
            allow_insecure_localhost=True,
        )
        adapter = AgentPlatformAdapter(
            transport,
            PlatformRequestContext(
                "tenant-a",
                "user-a",
                str(uuid4()),
                "00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01",
            ),
        )
        assert adapter.health() is True
        assert adapter.get_principal().user_id == "user-a"
        assert adapter.list_agents()[0].name == "security"
        assert adapter.list_capabilities(agent_id="agent-a")[0].capability_id == "repository.read"
        run = adapter.create_run(task_id="task-a", agent_id="agent-a", intent="inspect")
        assert run.state == "running"
        approval = adapter.request_approval(
            run_id=run.run_id,
            action="security.scan",
            resource="repo:example",
            reason="governed scan",
        )
        assert approval.approval_id == "approval-a"
        assert adapter.get_events(run_id=run.run_id)[0].event_type == "run.created"
        assert adapter.get_evidence(run_id=run.run_id)[0].evidence_id == "evidence-a"
        assert adapter.cancel_run(run_id=run.run_id).state == "cancelled"

        assert all("Authorization" not in call for call in ContractHandler.calls)
        assert all("tenant_id" in call and "subject_id" in call for call in ContractHandler.calls)
        assert all("operation" in call for call in ContractHandler.calls)
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def test_adapter_does_not_retry_non_idempotent_operations() -> None:
    class CountingHandler(ContractHandler):
        attempts = 0

        def do_POST(self) -> None:  # noqa: N802
            type(self).attempts += 1
            self.send_response(503)
            self.send_header("Content-Length", "0")
            self.end_headers()

    server = ThreadingHTTPServer(("127.0.0.1", 0), CountingHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        transport = HttpPlatformTransport(
            f"http://127.0.0.1:{server.server_address[1]}",
            StaticAccessTokenProvider("test-token"),
            allow_insecure_localhost=True,
            max_retries=3,
        )
        adapter = AgentPlatformAdapter(
            transport,
            PlatformRequestContext("tenant-a", "user-a", str(uuid4())),
        )
        with contextlib.suppress(Exception):
            adapter.create_run(task_id="task-a", agent_id="agent-a", intent="inspect")
        assert CountingHandler.attempts == 1
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)
