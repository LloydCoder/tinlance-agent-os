from datetime import UTC, datetime

from tinlance_agent_os.platform_adapter import AgentPlatformAdapter
from tinlance_agent_os.transport import PlatformRequestContext


class FakeTransport:
    def __init__(self) -> None:
        self.calls: list[tuple[str, dict[str, object], bool, str]] = []

    def send(self, *, operation, payload, context, idempotent):
        assert context.tenant_id == "tenant-1"
        self.calls.append((operation, dict(payload), idempotent, context.request_id))
        responses = {
            "principal.get": {"user_id": "user-1"},
            "agents.list": {"agents": [{"agent_id": "a1", "name": "Builder", "version": "1.2"}]},
            "runs.create": {"run_id": "r1", "task_id": "t1", "state": "running"},
            "runs.cancel": {"run_id": "r1", "task_id": "t1", "state": "cancelled"},
            "capabilities.list": {"capabilities": [{"capability_id": "cap.read"}]},
            "approvals.request": {"approval_id": "ap1"},
            "runs.events": {
                "events": [
                    {
                        "event_id": "e1",
                        "event_type": "run.started",
                        "occurred_at": "2026-09-28T10:00:00Z",
                        "workspace_id": "ws1",
                        "correlation_id": "c1",
                        "payload": {},
                    }
                ]
            },
            "runs.evidence": {"evidence": [{"evidence_id": "ev1"}]},
            "health": {"ready": True},
        }
        return responses[operation]


def test_adapter_implements_all_boundary_operations() -> None:
    transport = FakeTransport()\n    adapter = AgentPlatformAdapter(transport, PlatformRequestContext("tenant-1", "user-1"))
    assert adapter.get_principal().user_id == "user-1"
    assert adapter.list_agents()[0].agent_id == "a1"
    assert adapter.create_run(task_id="t1", agent_id="a1", intent="build").run_id == "r1"
    assert adapter.cancel_run(run_id="r1").state == "cancelled"
    assert adapter.list_capabilities(agent_id="a1")[0].capability_id == "cap.read"
    assert adapter.request_approval(run_id="r1", action="deploy").approval_id == "ap1"
    assert adapter.get_events(run_id="r1")[0].event_id == "e1"
    assert adapter.get_evidence(run_id="r1")[0].evidence_id == "ev1"
    assert adapter.health()\n    request_ids = [call[3] for call in transport.calls]\n    assert len(request_ids) == len(set(request_ids))
