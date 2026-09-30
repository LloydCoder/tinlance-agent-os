from pathlib import Path

import pytest

from tinlance_agent_os.domain import Session, SessionState, Task
from tinlance_agent_os.store import StateStore
from tinlance_agent_os.workspace import (
    ChannelKind,
    ChannelRuntime,
    WorkspaceError,
)


def seed(tmp_path: Path) -> tuple[StateStore, Session, Task]:
    store = StateStore(tmp_path / "state.db")
    store.upsert_workspace("ws-1", "user-1", "2026-09-30T00:00:00+00:00")
    session = Session("session-1", "ws-1", "user-1", "agent-1")
    task = Task(
        "task-1",
        "ws-1",
        "session-1",
        "agent-1",
        "research",
        SessionState.ACTIVE,
    )
    store.upsert_session(
        (
            session.session_id,
            session.workspace_id,
            session.user_id,
            session.agent_id,
            session.state.value,
            "2026-09-30T00:00:00+00:00",
        )
    )
    store.upsert_task(
        (
            task.task_id,
            task.workspace_id,
            task.session_id,
            task.agent_id,
            task.intent,
            task.state.value,
            "[]",
            "[]",
            "2026-09-30T00:00:00+00:00",
        )
    )
    return store, session, task


def test_channel_handoff_preserves_lifecycle_identity_and_trace(tmp_path: Path) -> None:
    store, session, task = seed(tmp_path)
    runtime = ChannelRuntime(store)
    web = runtime.register(workspace_id="ws-1", kind=ChannelKind.WEB, endpoint_id="browser")
    web = runtime.bind(
        web, session_id=session.session_id, task_id=task.task_id, agent_id=task.agent_id
    )
    cli = runtime.register(workspace_id="ws-1", kind=ChannelKind.CLI, endpoint_id="terminal")
    cli = runtime.handoff(web, runtime.bind(cli))
    assert cli.session_id == web.session_id
    assert cli.task_id == web.task_id
    assert cli.agent_id == web.agent_id
    assert cli.trace_id == web.trace_id


def test_all_channel_classes_share_one_runtime(tmp_path: Path) -> None:
    store, session, task = seed(tmp_path)
    runtime = ChannelRuntime(store)
    for kind in ChannelKind:
        context = runtime.register(workspace_id="ws-1", kind=kind, endpoint_id=kind.value)
        context = runtime.bind(
            context,
            session_id=session.session_id,
            task_id=task.task_id,
            agent_id=task.agent_id,
        )
        adapter = runtime.adapter(context)
        envelope = runtime.envelope(context, {"kind": kind.value})
        adapter.send(envelope)
    rows = store.query(
        "SELECT kind, session_id, task_id, trace_id FROM channels "
        "JOIN channel_bindings USING(channel_id) WHERE workspace_id=?",
        ("ws-1",),
    )
    assert len(rows) == 6
    assert all(row["session_id"] == session.session_id for row in rows)
    assert all(row["task_id"] == task.task_id for row in rows)
    assert all(row["trace_id"] == rows[0]["trace_id"] for row in rows)


def test_cross_workspace_handoff_is_denied(tmp_path: Path) -> None:
    store, session, task = seed(tmp_path)
    store.upsert_workspace("ws-2", "user-2", "2026-09-30T00:00:00+00:00")
    runtime = ChannelRuntime(store)
    first = runtime.register(workspace_id="ws-1", kind=ChannelKind.API, endpoint_id="api")
    first = runtime.bind(
        first, session_id=session.session_id, task_id=task.task_id, agent_id=task.agent_id
    )
    second = runtime.register(workspace_id="ws-2", kind=ChannelKind.API, endpoint_id="api")
    with pytest.raises(WorkspaceError, match="workspace"):
        runtime.handoff(first, second)


def test_wrong_task_agent_identity_is_denied(tmp_path: Path) -> None:
    store, session, task = seed(tmp_path)
    runtime = ChannelRuntime(store)
    context = runtime.register(workspace_id="ws-1", kind=ChannelKind.WEB, endpoint_id="browser")
    with pytest.raises(WorkspaceError, match="agent"):
        runtime.bind(
            context,
            session_id=session.session_id,
            task_id=task.task_id,
            agent_id="forged-agent",
        )


def test_workspace_snapshot_includes_core_and_registered_resources(tmp_path: Path) -> None:
    store, session, task = seed(tmp_path)
    runtime = ChannelRuntime(store)
    runtime.register_resource(
        workspace_id="ws-1",
        resource_type="applications",
        resource_id="app-1",
        metadata={"version": "1.0.0"},
    )
    runtime.register_resource(
        workspace_id="ws-1",
        resource_type="skills",
        resource_id="skill-1",
    )
    runtime.register_resource(
        workspace_id="ws-1",
        resource_type="integrations",
        resource_id="connector-1",
    )
    context = runtime.register(
        workspace_id="ws-1", kind=ChannelKind.NOTIFICATIONS, endpoint_id="push"
    )
    snapshot = runtime.workspace_snapshot("ws-1")
    assert session.session_id in snapshot.sessions
    assert task.task_id in snapshot.tasks
    assert "app-1" in snapshot.applications
    assert "skill-1" in snapshot.skills
    assert "connector-1" in snapshot.integrations
    assert context.channel_id in snapshot.channels



# M19 acceptance: channel identity and trace continuity are durable invariants.
