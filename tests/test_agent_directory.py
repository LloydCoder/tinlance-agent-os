from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest

from tinlance_agent_os.agent_directory import (
    AgentDirectory,
    Compatibility,
    DesiredAgent,
    DesiredAgentState,
    ReconciliationAction,
)
from tinlance_agent_os.agent_runtime import (
    AgentDefinition,
    AgentRuntime,
    RestartPolicy,
    RuntimeConfig,
)
from tinlance_agent_os.store import StateStore


def make_directory(tmp_path: Path) -> tuple[StateStore, AgentDirectory]:
    store = StateStore(tmp_path / "state.db")
    return store, AgentDirectory(store)


def desired(
    *, generation: int = 1, state: DesiredAgentState = DesiredAgentState.RUNNING
) -> DesiredAgent:
    return DesiredAgent(
        agent_id="agent-1",
        workspace_id="workspace-1",
        name="Research",
        version="1.2.3",
        entrypoint="research.main",
        desired_state=state,
        capabilities=("research.read",),
        configuration={"model": "test"},
        compatibility=Compatibility(minimum_os_version="0.1.0", platform_contract="1.1"),
        generation=generation,
    )


def register(store: StateStore) -> AgentRuntime:
    runtime = AgentRuntime(
        store,
        AgentDefinition(
            "agent-1",
            "workspace-1",
            "Research",
            "1.2.3",
            "research.main",
            capabilities=("research.read",),
            configuration={"model": "test"},
            restart_policy=RestartPolicy(max_restarts=1),
            runtime=RuntimeConfig(heartbeat_interval_seconds=0.1, heartbeat_timeout_seconds=1),
        ),
        lambda _: "ok",
    )
    runtime.register()
    runtime.validate()
    return runtime


def test_desired_state_is_durable_and_generationed(tmp_path: Path) -> None:
    store, directory = make_directory(tmp_path)
    saved = directory.set_desired(desired())
    assert saved.generation == 1
    assert directory.get_desired("agent-1") == saved

    updated = directory.set_desired(
        desired(state=DesiredAgentState.PAUSED),
        expected_generation=saved.generation,
    )
    assert updated.generation == 2
    assert directory.get_desired("agent-1") == updated

    with pytest.raises(ValueError, match="generation conflict"):
        directory.set_desired(
            desired(state=DesiredAgentState.STOPPED),
            expected_generation=1,
        )


def test_reconciliation_is_read_only_and_detects_lifecycle_drift(tmp_path: Path) -> None:
    store, directory = make_directory(tmp_path)
    directory.set_desired(desired())
    assert directory.plan("agent-1").action is ReconciliationAction.BLOCKED

    runtime = register(store)
    plan = directory.plan("agent-1")
    assert plan.action is ReconciliationAction.START

    runtime.start()
    assert directory.plan("agent-1").action is ReconciliationAction.NOOP


def test_reconciliation_detects_version_and_configuration_drift(tmp_path: Path) -> None:
    store, directory = make_directory(tmp_path)
    runtime = register(store)
    runtime.start()
    directory.set_desired(desired())

    changed = replace(desired(), version="2.0.0")
    directory.set_desired(changed, expected_generation=1)
    assert directory.plan("agent-1").action is ReconciliationAction.UPGRADE


def test_desired_state_does_not_grant_platform_authority(tmp_path: Path) -> None:
    _, directory = make_directory(tmp_path)
    saved = directory.set_desired(desired())
    assert saved.capabilities == ("research.read",)
    assert directory.plan("agent-1").action is ReconciliationAction.BLOCKED
