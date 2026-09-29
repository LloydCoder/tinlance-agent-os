from __future__ import annotations

import pytest

from tinlance_agent_os.client import ReferenceAgentPlatformClient
from tinlance_agent_os.daemon_service import LocalOSService
from tinlance_agent_os.store import StateStore


def test_dispatch_requires_durable_os_task(tmp_path) -> None:
    service = LocalOSService(StateStore(tmp_path / "state.db"), ReferenceAgentPlatformClient())
    with pytest.raises(PermissionError):
        service.handle(
            {
                "operation": "dispatch",
                "task_id": "missing",
            }
        )


def test_platform_run_lifecycle_updates_os_task_state(tmp_path) -> None:
    service = LocalOSService(StateStore(tmp_path / "state.db"), ReferenceAgentPlatformClient())
    workspace = service.create_workspace("user-1")
    session = service.create_session(workspace.workspace_id, "user-1", "agent-1")
    task = service.create_task(workspace.workspace_id, session.session_id, "agent-1", "inspect")
    run = service.dispatch(task)
    row = service.store.get_task(task.task_id)
    assert row is not None
    assert row["state"] == "running"
    assert run.run_id in row["platform_run_ids"]

    cancelled = service.cancel(run.run_id)
    assert cancelled.state == "cancelled"
    row = service.store.get_task(task.task_id)
    assert row is not None
    assert row["state"] == "cancelled"


def test_approval_moves_local_task_to_waiting_approval(tmp_path) -> None:
    service = LocalOSService(StateStore(tmp_path / "state.db"), ReferenceAgentPlatformClient())
    workspace = service.create_workspace("user-1")
    session = service.create_session(workspace.workspace_id, "user-1", "agent-1")
    task = service.create_task(workspace.workspace_id, session.session_id, "agent-1", "deploy")
    run = service.dispatch(task)
    approval = service.request_approval(run.run_id, "deploy", "service:api", "production change")
    assert approval.approval_id
    row = service.store.get_task(task.task_id)
    assert row is not None
    assert row["state"] == "waiting_approval"