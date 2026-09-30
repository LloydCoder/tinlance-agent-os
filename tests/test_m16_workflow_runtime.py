from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from tinlance_agent_os.store import StateStore
from tinlance_agent_os.workflow import (
    RetryPolicy,
    WorkflowDefinition,
    WorkflowStep,
    WorkflowStepKind,
    WorkflowStepResult,
    WorkflowStepState,
    WorkflowState,
)
from tinlance_agent_os.workflow_runtime import (
    DurableWorkflowRuntime,
    RetryableWorkflowError,
)


class FakeExecutor:
    def __init__(self) -> None:
        self.calls: list[str] = []
        self.run_ids: dict[str, str] = {}
        self.fail_once: set[str] = set()
        self.crash_once: set[str] = set()
        self.cancelled: list[str] = []
        self.approvals: list[str] = []

    def execute(self, *, workspace_id, workflow_instance_id, step, context, idempotency_key, timeout_seconds):
        if idempotency_key in self.crash_once:
            self.crash_once.remove(idempotency_key)
            self.calls.append(idempotency_key)
            raise SystemExit("simulated process crash")
        if idempotency_key in self.fail_once:
            self.fail_once.remove(idempotency_key)
            raise RetryableWorkflowError("transient")
        if idempotency_key not in self.run_ids:
            self.calls.append(idempotency_key)
            self.run_ids[idempotency_key] = f"run-{len(self.run_ids)+1}"
        return WorkflowStepResult(
            WorkflowStepState.COMPLETED,
            output={"step": step.step_id},
            platform_run_id=self.run_ids[idempotency_key],
        )

    def cancel(self, *, platform_run_id):
        self.cancelled.append(platform_run_id)

    def request_approval(self, *, workspace_id, workflow_instance_id, step, idempotency_key):
        approval = f"approval-{step.step_id}"
        self.approvals.append(approval)
        return approval

    def compensate(self, *, workspace_id, workflow_instance_id, step, context, idempotency_key):
        return WorkflowStepResult(WorkflowStepState.COMPLETED, output={"compensated": step.step_id})


def setup(tmp_path: Path, executor: FakeExecutor):
    store = StateStore(tmp_path / "state.db")
    store.upsert_workspace("ws", "owner", datetime.now(UTC).isoformat())
    return store, DurableWorkflowRuntime(store, executor)


def test_parallel_steps_checkpoint_and_resume(tmp_path):
    executor = FakeExecutor()
    store, runtime = setup(tmp_path, executor)
    definition = WorkflowDefinition(
        "wf",
        "ws",
        (
            WorkflowStep("a", "a"),
            WorkflowStep("b", "b"),
            WorkflowStep("c", "c", depends_on=("a", "b")),
        ),
    )
    instance = runtime.start(definition)
    result = runtime.run(instance.instance_id, definition)
    assert result.state == WorkflowState.COMPLETED
    assert len(executor.calls) == 3
    assert len(store.workflow_events(instance.instance_id)) >= 5


def test_retry_backoff_does_not_change_idempotency_key(tmp_path):
    executor = FakeExecutor()
    store, runtime = setup(tmp_path, executor)
    definition = WorkflowDefinition(
        "wf",
        "ws",
        (WorkflowStep("a", "a", retry=RetryPolicy(2, 0)),),
    )
    instance = runtime.start(definition)
    key = store.get_workflow_steps(instance.instance_id)[0]["idempotency_key"]
    executor.fail_once.add(key)
    result = runtime.run(instance.instance_id, definition)
    assert result.state == WorkflowState.COMPLETED
    assert executor.calls == [key]


def test_approval_pause_and_resume(tmp_path):
    executor = FakeExecutor()
    store, runtime = setup(tmp_path, executor)
    definition = WorkflowDefinition(
        "wf",
        "ws",
        (
            WorkflowStep("approve", "approve", kind=WorkflowStepKind.APPROVAL),
            WorkflowStep("after", "after", depends_on=("approve",)),
        ),
    )
    instance = runtime.start(definition)
    paused = runtime.run(instance.instance_id, definition)
    assert paused.state == WorkflowState.WAITING_APPROVAL
    assert executor.approvals == ["approval-approve"]
    done = runtime.approve(instance.instance_id, definition, "approve", True)
    assert done.state == WorkflowState.COMPLETED


def test_human_input_pause_and_resume(tmp_path):
    executor = FakeExecutor()
    _, runtime = setup(tmp_path, executor)
    definition = WorkflowDefinition(
        "wf",
        "ws",
        (
            WorkflowStep("input", "input", kind=WorkflowStepKind.HUMAN_INPUT, human_input_key="answer"),
            WorkflowStep("after", "after", depends_on=("input",)),
        ),
    )
    instance = runtime.start(definition)
    paused = runtime.run(instance.instance_id, definition)
    assert paused.state == WorkflowState.WAITING_INPUT
    done = runtime.provide_input(instance.instance_id, definition, "input", "accepted")
    assert done.state == WorkflowState.COMPLETED
    assert done.context["answer"] == "accepted"


def test_condition_skips_action_without_executing_it(tmp_path):
    executor = FakeExecutor()
    _, runtime = setup(tmp_path, executor)
    definition = WorkflowDefinition(
        "wf",
        "ws",
        (WorkflowStep("guard", "guard", kind=WorkflowStepKind.CONDITION, condition="enabled"),
         WorkflowStep("action", "action", depends_on=("guard",), condition="enabled")),
    )
    instance = runtime.start(definition, context={"enabled": False})
    result = runtime.run(instance.instance_id, definition)
    assert result.state == WorkflowState.COMPLETED
    assert executor.calls == []


def test_process_crash_recovers_running_step_without_duplicate_side_effect(tmp_path):
    executor = FakeExecutor()
    store, runtime = setup(tmp_path, executor)
    definition = WorkflowDefinition("wf", "ws", (WorkflowStep("a", "a"),))
    instance = runtime.start(definition)
    key = store.get_workflow_steps(instance.instance_id)[0]["idempotency_key"]
    executor.crash_once.add(key)
    with pytest.raises(SystemExit):
        runtime.run(instance.instance_id, definition)
    assert store.get_workflow_steps(instance.instance_id)[0]["state"] == WorkflowStepState.RUNNING.value

    recovered = runtime.recover({"wf": definition})
    assert recovered[0].state == WorkflowState.COMPLETED
    assert executor.calls == [key]


def test_cancellation_propagates_to_platform_run(tmp_path):
    executor = FakeExecutor()
    store, runtime = setup(tmp_path, executor)
    definition = WorkflowDefinition("wf", "ws", (WorkflowStep("a", "a"),))
    instance = runtime.start(definition)
    runtime.run(instance.instance_id, definition)
    # Completed runs are not cancellable; a waiting approval provides a durable pause to cancel.
    waiting_def = WorkflowDefinition(
        "wf2", "ws",
        (WorkflowStep("approve", "approve", kind=WorkflowStepKind.APPROVAL),),
    )
    waiting = runtime.start(waiting_def)
    paused = runtime.run(waiting.instance_id, waiting_def)
    cancelled = runtime.cancel(paused.instance_id, waiting_def)
    assert cancelled.state == WorkflowState.CANCELLED
    assert store.get_workflow_instance(paused.instance_id)["cancel_requested"] == 1


def test_deadline_fails_closed(tmp_path):
    executor = FakeExecutor()
    _, runtime = setup(tmp_path, executor)
    definition = WorkflowDefinition("wf", "ws", (WorkflowStep("a", "a"),), deadline_seconds=1)
    instance = runtime.start(definition)
    row = runtime.store.get_workflow_instance(instance.instance_id)
    runtime.store.update_workflow_instance(
        instance_id=instance.instance_id,
        expected_version=int(row["version"]),
        state=WorkflowState.RUNNING.value,
        checkpoint=None,
        context="{}",
        cancel_requested=False,
        updated_at=datetime.now(UTC).isoformat(),
    )
    runtime.store.query("SELECT instance_id FROM workflow_instances WHERE instance_id=?", (instance.instance_id,))
    # The deadline is computed at start; move it to the past through the durable row for deterministic testing.
    with __import__("sqlite3").connect(runtime.store.path) as db:
        db.execute("UPDATE workflow_instances SET deadline_at=? WHERE instance_id=?",
                   ((datetime.now(UTC) - timedelta(seconds=1)).isoformat(), instance.instance_id))
        db.commit()
    result = runtime.run(instance.instance_id, definition)
    assert result.state == WorkflowState.FAILED
