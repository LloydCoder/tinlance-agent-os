from __future__ import annotations

import sqlite3
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from tinlance_agent_os.agent_runtime import (
    AgentDefinition,
    AgentLifecycleState,
    AgentRuntime,
    HealthState,
    RestartPolicy,
    RuntimeConfig,
    recover_orphans,
)
from tinlance_agent_os.store import StateStore


def make_runtime(
    tmp_path: Path,
    *,
    worker: object | None = None,
    restart: RestartPolicy | None = None,
) -> tuple[StateStore, AgentRuntime]:
    store = StateStore(tmp_path / "state.db")
    definition = AgentDefinition(
        "agent-1",
        "workspace-1",
        "Research",
        "1.2.3",
        "research.main",
        capabilities=("research.read",),
        configuration={"model": "test"},
        restart_policy=restart or RestartPolicy(enabled=True, max_restarts=2),
        runtime=RuntimeConfig(
            heartbeat_interval_seconds=0.01,
            heartbeat_timeout_seconds=0.05,
        ),
    )
    callback = worker if callable(worker) else (lambda _: "ok")
    return store, AgentRuntime(store, definition, callback)


def test_full_lifecycle_is_durable_and_deterministic(tmp_path: Path) -> None:
    store, agent = make_runtime(tmp_path)
    assert agent.register().state is AgentLifecycleState.REGISTERED
    assert agent.validate().state is AgentLifecycleState.READY
    assert agent.start().state is AgentLifecycleState.RUNNING
    assert agent.run() == "ok"
    assert agent.health() is HealthState.HEALTHY
    assert agent.pause().state is AgentLifecycleState.PAUSED
    assert agent.resume().state is AgentLifecycleState.RUNNING
    assert agent.stop().state is AgentLifecycleState.STOPPED

    events = store.agent_events("agent-1")
    assert [event["event_type"] for event in events] == [
        "agent.registered",
        "agent.validation.started",
        "agent.validation.succeeded",
        "agent.starting",
        "agent.started",
        "agent.pausing",
        "agent.paused",
        "agent.resuming",
        "agent.resumed",
        "agent.stopping",
        "agent.stopped",
    ]
    assert [event["sequence"] for event in events] == list(range(1, len(events) + 1))
    assert len({event["event_id"] for event in events}) == len(events)

    reopened = AgentRuntime(store, agent.definition, lambda _: "ok")
    assert reopened.snapshot().state is AgentLifecycleState.STOPPED
    assert reopened.snapshot().definition.version == "1.2.3"


def test_version_binding_rejects_substitution(tmp_path: Path) -> None:
    store, agent = make_runtime(tmp_path)
    agent.register()
    replacement = AgentRuntime(
        store,
        AgentDefinition("agent-1", "workspace-1", "Research", "9.9.9", "research.main"),
        lambda _: None,
    )
    with pytest.raises(ValueError, match="version"):
        replacement.register()


def test_invalid_definition_and_lifecycle_operations_fail_closed(tmp_path: Path) -> None:
    store, agent = make_runtime(tmp_path)
    with pytest.raises(ValueError, match="heartbeat_timeout"):
        AgentDefinition(
            "a", "w", "A", "1", "x", runtime=RuntimeConfig(2, 1)
        ).validate()
    with pytest.raises(ValueError, match="max_restarts"):
        RestartPolicy(max_restarts=-1).validate()

    agent.register()
    with pytest.raises(ValueError, match="invalid lifecycle operation"):
        agent.pause()
    agent.validate()
    with pytest.raises(ValueError, match="invalid lifecycle operation"):
        agent.resume()


def test_crash_is_recorded_and_restart_policy_recovers(tmp_path: Path) -> None:
    attempts = 0

    def failing(_: object) -> None:
        nonlocal attempts
        attempts += 1
        raise RuntimeError("boom")

    store, agent = make_runtime(tmp_path, worker=failing)
    agent.register()
    agent.validate()
    agent.start()
    with pytest.raises(RuntimeError, match="boom"):
        agent.run()

    assert agent.snapshot().state is AgentLifecycleState.RUNNING
    assert agent.snapshot().restart_count == 1
    assert attempts == 1
    assert any(event["event_type"] == "agent.crashed" for event in store.agent_events("agent-1"))
    assert any(event["event_type"] == "agent.recovered" for event in store.agent_events("agent-1"))


def test_restart_policy_exhaustion_fails_closed(tmp_path: Path) -> None:
    store, agent = make_runtime(
        tmp_path,
        restart=RestartPolicy(enabled=True, max_restarts=0),
    )
    agent.register()
    agent.validate()
    agent.start()
    agent._transition(AgentLifecycleState.CRASHED, "agent.crashed")
    assert agent.recover().state is AgentLifecycleState.FAILED
    assert store.get_agent("agent-1")["state"] == "failed"


def test_heartbeat_lease_expiry_is_detected_after_restart(tmp_path: Path) -> None:
    store, agent = make_runtime(tmp_path)
    agent.register()
    agent.validate()
    agent.start()
    expired = (datetime.now(UTC) - timedelta(seconds=1)).isoformat()
    with sqlite3.connect(store.path) as db:
        db.execute(
            "UPDATE agents SET lease_expires_at=? WHERE agent_id=?",
            (expired, "agent-1"),
        )

    assert recover_orphans(store) == ("agent-1",)
    assert store.get_agent("agent-1")["state"] == AgentLifecycleState.CRASHED.value
    assert store.agent_events("agent-1")[-1]["event_type"] == "agent.crash.detected"


def test_heartbeat_is_durable_and_requires_running_state(tmp_path: Path) -> None:
    store, agent = make_runtime(tmp_path)
    agent.register()
    agent.validate()
    agent.start()
    before = agent.snapshot()
    after = agent.heartbeat()
    assert after.last_heartbeat_at is not None
    assert after.lease_expires_at is not None
    assert after.state_version == before.state_version

    agent.stop()
    with pytest.raises(ValueError, match="invalid lifecycle operation"):
        agent.heartbeat()


def test_deterministic_event_id_is_stable() -> None:
    first = AgentRuntime.deterministic_event_id("agent-1", 7, "agent.started")
    second = AgentRuntime.deterministic_event_id("agent-1", 7, "agent.started")
    different = AgentRuntime.deterministic_event_id("agent-1", 8, "agent.started")
    assert first == second
    assert first != different
