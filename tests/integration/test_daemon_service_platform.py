from tinlance_agent_os.client import ReferenceAgentPlatformClient
from tinlance_agent_os.daemon_service import LocalOSService
from tinlance_agent_os.store import StateStore


def test_local_os_service_exposes_platform_lifecycle(tmp_path) -> None:
    service = LocalOSService(
        StateStore(tmp_path / "state.db"),
        ReferenceAgentPlatformClient(),
    )
    workspace = service.create_workspace("reference-user")
    session = service.create_session(workspace.workspace_id, "reference-user", "agent-a")
    task = service.create_task(
        workspace.workspace_id,
        session.session_id,
        "agent-a",
        "inspect repository",
    )

    run = service.dispatch(task)
    assert run.task_id == task.task_id
    assert service.handle({"operation": "health"}) == {"ready": True}
    assert service.handle({"operation": "principal"}) == {"user_id": "reference-user"}
    assert service.handle({"operation": "agents"}) == {"agents": []}
    assert service.handle({"operation": "capabilities", "agent_id": "agent-a"}) == {
        "capabilities": [{"capability_id": "agent:agent-a:capabilities"}]
    }

    dispatched = service.handle(
        {
            "operation": "dispatch",
            "task_id": task.task_id,
            "agent_id": "agent-a",
            "workspace_id": workspace.workspace_id,
            "session_id": session.session_id,
            "intent": "inspect repository",
        }
    )
    assert dispatched["state"] == "running"

    approval = service.handle(
        {
            "operation": "approval",
            "run_id": run.run_id,
            "action": "security.scan",
            "resource": "repo:example",
            "reason": "governed scan",
        }
    )
    assert approval["approval_id"].startswith("approval:")

    cancelled = service.handle({"operation": "cancel", "run_id": run.run_id})
    assert cancelled["state"] == "cancelled"
    assert service.handle({"operation": "events", "run_id": run.run_id}) == {"events": []}
    assert service.handle({"operation": "evidence", "run_id": run.run_id}) == {
        "evidence": [{"evidence_id": f"evidence:{run.run_id}", "source": "agent-platform"}]
    }


def test_local_os_service_rejects_unsupported_daemon_operation(tmp_path) -> None:
    service = LocalOSService(
        StateStore(tmp_path / "state.db"),
        ReferenceAgentPlatformClient(),
    )
    try:
        service.handle({"operation": "unsupported"})
    except ValueError as exc:
        assert str(exc) == "unsupported operation"
    else:
        raise AssertionError("unsupported operation must fail closed")
