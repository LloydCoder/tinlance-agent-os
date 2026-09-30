from __future__ import annotations

from pathlib import Path

import pytest

from tinlance_agent_os import (
    AgentSDK,
    CapabilityDeclaration,
    ContractValidationError,
    ExecutionContext,
    IdempotencyKey,
    TraceContext,
)
from tinlance_agent_os.client import ReferenceAgentPlatformClient
from tinlance_agent_os.domain import User
from tinlance_agent_os.store import StateStore
from tinlance_agent_os.workflow import WorkflowDefinition, WorkflowStep


def make_sdk(tmp_path: Path) -> tuple[AgentSDK, ReferenceAgentPlatformClient]:
    platform = ReferenceAgentPlatformClient(principal=User("user-1"))
    store = StateStore(tmp_path / "state.db")
    sdk = AgentSDK(platform, store)
    return sdk, platform


def test_reference_agent_golden_path_has_no_low_level_platform_calls(tmp_path: Path) -> None:
    sdk, platform = make_sdk(tmp_path)
    workspace = "workspace-1"
    store = sdk.store
    store.upsert_workspace(workspace, "user-1", "2026-09-30T00:00:00+00:00")
    app = sdk.scaffold(
        agent_id="research-agent",
        workspace_id=workspace,
        name="Research Agent",
        version="1.0.0",
        entrypoint="research.main",
        capabilities=(CapabilityDeclaration("research.read", "Read approved research sources"),),
    )
    runtime = app.runtime(store, lambda config: {"answer": "ok", "model": config["model"]})
    runtime.register()
    runtime.validate()
    runtime.start()

    session = sdk.session(workspace, "user-1", app.scaffold.definition.agent_id)
    task = sdk.task(session, "Research the requested subject")
    result = sdk.execute(task)

    assert result.run.task_id == task.task.task_id
    assert result.run.run_id
    assert platform.runs[result.run.run_id] == result.run
    assert result.evidence[0].evidence_id.startswith("evidence:")
    assert app.scaffold.manifest.capabilities[0].capability_id == "research.read"


def test_idempotency_is_durable_and_replay_safe(tmp_path: Path) -> None:
    sdk, platform = make_sdk(tmp_path)
    sdk.store.upsert_workspace("w", "u", "2026-09-30T00:00:00+00:00")
    app = sdk.scaffold(
        agent_id="a",
        workspace_id="w",
        name="A",
        version="1.0.0",
        entrypoint="a.main",
    )
    sdk.register(app)
    session = sdk.session("w", "u", "a")
    task = sdk.task(session, "do work")
    key = IdempotencyKey("stable-operation-key")

    first = sdk.execute(task, idempotency_key=key)
    second = sdk.execute(task, idempotency_key=key)

    assert first.run.run_id == second.run.run_id
    assert len(platform.runs) == 1
    rows = sdk.store.query(
        "SELECT state,result_id FROM sdk_idempotency WHERE idempotency_key=?",
        (key.value,),
    )
    assert rows[0]["state"] == "completed"
    assert rows[0]["result_id"] == first.run.run_id


def test_approval_is_idempotent_and_opaque(tmp_path: Path) -> None:
    sdk, _ = make_sdk(tmp_path)
    sdk.store.upsert_workspace("w", "u", "2026-09-30T00:00:00+00:00")
    app = sdk.scaffold(
        agent_id="a",
        workspace_id="w",
        name="A",
        version="1.0.0",
        entrypoint="a.main",
    )
    sdk.register(app)
    session = sdk.session("w", "u", "a")
    task = sdk.task(session, "send report")
    result = sdk.execute(task)
    key = IdempotencyKey("approval-key")

    first = sdk.approve(
        result,
        action="send",
        resource="report:1",
        reason="User requested delivery",
        idempotency_key=key,
    )
    second = sdk.approve(
        result,
        action="send",
        resource="report:1",
        reason="User requested delivery",
        idempotency_key=key,
    )

    assert first.reference.approval_id == second.reference.approval_id
    assert first.state.value == "requested"


def test_context_and_trace_propagate_through_handles(tmp_path: Path) -> None:
    sdk, _ = make_sdk(tmp_path)
    sdk.store.upsert_workspace("w", "u", "2026-09-30T00:00:00+00:00")
    app = sdk.scaffold(
        agent_id="a",
        workspace_id="w",
        name="A",
        version="1.0.0",
        entrypoint="a.main",
    )
    sdk.register(app)
    context = ExecutionContext(
        trace=TraceContext("00-0123456789abcdef0123456789abcdef-0123456789abcdef-01"),
        baggage={"tenant": "w"},
    )
    with sdk.context(context):
        session = sdk.session("w", "u", "a")
        task = sdk.task(session, "trace me")
        assert task.context.trace == context.trace
        assert task.context.session_id == session.session.session_id
        assert sdk.current_context() == context


def test_workflow_helpers_are_typed_and_validated(tmp_path: Path) -> None:
    sdk, _ = make_sdk(tmp_path)
    definition = WorkflowDefinition(
        "wf-1",
        "w",
        (
            WorkflowStep("research", "research"),
            WorkflowStep("review", "review", ("research",)),
        ),
    )
    workflow = sdk.workflow(definition)
    workflow = sdk.workflow_complete_step(workflow, "research")
    workflow = sdk.workflow_complete_step(workflow, "review")
    assert workflow.execution.state.value == "completed"


def test_manifest_and_capability_contracts_fail_closed(tmp_path: Path) -> None:
    sdk, _ = make_sdk(tmp_path)
    with pytest.raises(ContractValidationError):
        sdk.scaffold(
            agent_id="a",
            workspace_id="w",
            name="A",
            version="1.0.0",
            entrypoint=" a.main",
        )
    with pytest.raises(ValueError):
        TraceContext("invalid")
    with pytest.raises(ValueError):
        sdk.scaffold(
            agent_id="a",
            workspace_id="w",
            name="A",
            version="1.0.0",
            entrypoint="a.main",
            capabilities=(
                CapabilityDeclaration("x", "one"),
                CapabilityDeclaration("x", "two"),
            ),
        )
