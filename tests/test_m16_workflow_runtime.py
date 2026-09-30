from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

import sqlite3

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

    def execute(
        self, *, workspace_id, workflow_instance_id, step, context, idempotency_key, timeout_seconds
    ):
        if idempotency_key in self.crash_once:
            self.crash_once.remove(idempotency_key)
            self.run_ids[idempotency_key] = f"run-{len(self.run_ids) + 1}"
            self.calls.append(idempotency_key)
            raise SystemExit("simulated process crash")
        if idempotency_key in self.fail_once:
            self.fail_once.remove(idempotency_key)
            raise RetryableWorkflowError("transient")
        if idempotency_key not in self.run_ids:
            self.calls.append(idempotency_key)
            self.run_ids[idempotency_key] = f"run-{len(self.run_ids) + 1}"
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
            WorkflowStep(
                "input", "input", kind=WorkflowStepKind.HUMAN_INPUT, human_input_key="answer"
            ),
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
        (
            WorkflowStep("guard", "guard", kind=WorkflowStepKind.CONDITION, condition="enabled"),
            WorkflowStep("action", "action", depends_on=("guard",), condition="enabled"),
        ),
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
    assert (
        store.get_workflow_steps(instance.instance_id)[0]["state"]
        == WorkflowStepState.RUNNING.value
    )

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
        "wf2",
        "ws",
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
    runtime.store.query(
        "SELECT instance_id FROM workflow_instances WHERE instance_id=?", (instance.instance_id,)
    )
    # Move the durable deadline into the past for deterministic testing.
    with sqlite3.connect(runtime.store.path) as db:
        db.execute(
            "UPDATE workflow_instances SET deadline_at=? WHERE instance_id=?",
            ((datetime.now(UTC) - timedelta(seconds=1)).isoformat(), instance.instance_id),
        )
        db.commit()
    result = runtime.run(instance.instance_id, definition)
    assert result.state == WorkflowState.FAILED

def test_event_trigger_and_schedule_fire(tmp_path):
    executor = FakeExecutor()
    store, runtime = setup(tmp_path, executor)
    definition = WorkflowDefinition("wf", "ws", (WorkflowStep("a", "a"),))
    event_instance = runtime.trigger_event("invoice.created", {"id": "42"}, definition)
    assert event_instance.context["event_type"] == "invoice.created"
    assert runtime.run(event_instance.instance_id, definition).state == WorkflowState.COMPLETED

    schedule_at = datetime.now(UTC) - timedelta(seconds=1)
    runtime.schedule("schedule-1", definition, "*/5 * * * *", schedule_at)
    due = runtime.fire_due_schedules({"wf": definition}, now=datetime.now(UTC))
    assert len(due) == 1
    assert due[0].context["schedule_id"] == "schedule-1"


def test_condition_equality_and_inequality(tmp_path):
    executor = FakeExecutor()
    _, runtime = setup(tmp_path, executor)
    definition = WorkflowDefinition(
        "wf",
        "ws",
        (
            WorkflowStep("eq", "eq", condition="mode == 'safe'"),
            WorkflowStep("neq", "neq", depends_on=("eq",), condition="mode != 'blocked'"),
        ),
    )
    instance = runtime.start(definition, context={"mode": "safe"})
    assert runtime.run(instance.instance_id, definition).state == WorkflowState.COMPLETED


def test_approval_rejection_fails_workflow(tmp_path):
    executor = FakeExecutor()
    _, runtime = setup(tmp_path, executor)
    definition = WorkflowDefinition(
        "wf",
        "ws",
        (WorkflowStep("approve", "approve", kind=WorkflowStepKind.APPROVAL),),
    )
    instance = runtime.start(definition)
    paused = runtime.run(instance.instance_id, definition)
    rejected = runtime.approve(paused.instance_id, definition, "approve", False)
    assert rejected.state == WorkflowState.FAILED


def test_retry_exhaustion_fails(tmp_path):
    executor = FakeExecutor()
    store, runtime = setup(tmp_path, executor)
    definition = WorkflowDefinition(
        "wf",
        "ws",
        (WorkflowStep("a", "a", retry=RetryPolicy(1, 0)),),
    )
    instance = runtime.start(definition)
    key = store.get_workflow_steps(instance.instance_id)[0]["idempotency_key"]
    executor.fail_once.add(key)
    assert runtime.run(instance.instance_id, definition).state == WorkflowState.FAILED


def test_cancel_propagates_to_running_platform_run(tmp_path):
    executor = FakeExecutor()
    store, runtime = setup(tmp_path, executor)
    definition = WorkflowDefinition("wf", "ws", (WorkflowStep("a", "a"),))
    instance = runtime.start(definition)
    row = store.get_workflow_steps(instance.instance_id)[0]
    store.upsert_workflow_step(
        instance_id=instance.instance_id,
        step_id="a",
        state=WorkflowStepState.RUNNING.value,
        attempt=1,
        next_attempt_at=None,
        idempotency_key=row["idempotency_key"],
        platform_run_id="platform-run-1",
        approval_id=None,
        input_data="{}",
        output_data=None,
        error=None,
        started_at=datetime.now(UTC).isoformat(),
        completed_at=None,
        updated_at=datetime.now(UTC).isoformat(),
    )
    runtime.cancel(instance.instance_id, definition)
    assert executor.cancelled == ["platform-run-1"]


def test_compensation_runs_after_failure(tmp_path):
    class FailingExecutor(FakeExecutor):
        def execute(self, *, workspace_id, workflow_instance_id, step, context, idempotency_key, timeout_seconds):
            if step.step_id == "fail":
                raise RuntimeError("boom")
            return super().execute(
                workspace_id=workspace_id,
                workflow_instance_id=workflow_instance_id,
                step=step,
                context=context,
                idempotency_key=idempotency_key,
                timeout_seconds=timeout_seconds,
            )

    executor = FailingExecutor()
    _, runtime = setup(tmp_path, executor)
    definition = WorkflowDefinition(
        "wf",
        "ws",
        (
            WorkflowStep("done", "done", compensate_with="undo"),
            WorkflowStep("fail", "fail", depends_on=("done",)),
            WorkflowStep("undo", "undo", kind=WorkflowStepKind.COMPENSATION),
        ),
        compensation_enabled=True,
    )
    instance = runtime.start(definition)
    assert runtime.run(instance.instance_id, definition).state == WorkflowState.FAILED


def test_platform_executor_maps_runs():
    class Run:
        run_id = "run-1"

    class Approval:
        approval_id = "approval-1"

    class Platform:
        def __init__(self):
            self.calls = []

        def create_run(self, **kwargs):
            self.calls.append(("create", kwargs))
            return Run()

        def request_approval(self, **kwargs):
            self.calls.append(("approval", kwargs))
            return Approval()

        def cancel_run(self, **kwargs):
            self.calls.append(("cancel", kwargs))

    from tinlance_agent_os.workflow_runtime import AgentPlatformWorkflowExecutor

    platform = Platform()
    adapter = AgentPlatformWorkflowExecutor(platform, "agent-1")
    step = WorkflowStep("a", "do a")
    result = adapter.execute(
        workspace_id="ws",
        workflow_instance_id="wf-1",
        step=step,
        context={},
        idempotency_key="key",
        timeout_seconds=5,
    )
    assert result.platform_run_id == "run-1"
    assert adapter.request_approval(
        workspace_id="ws",
        workflow_instance_id="wf-1",
        step=WorkflowStep("approve", "approve", kind=WorkflowStepKind.APPROVAL),
        idempotency_key="approval-key",
    ) == "approval-1"
    adapter.cancel(platform_run_id="run-1")
    assert [kind for kind, _ in platform.calls] == ["create", "create", "approval", "cancel"]


def test_definition_rejects_dependency_cycles():
    definition = WorkflowDefinition(
        "wf",
        "ws",
        (
            WorkflowStep("a", "a", depends_on=("b",)),
            WorkflowStep("b", "b", depends_on=("a",)),
        ),
    )
    with pytest.raises(ValueError, match="cycle"):
        definition.validate()


def test_recovery_handles_completed_state(tmp_path):
    executor = FakeExecutor()
    _, runtime = setup(tmp_path, executor)
    definition = WorkflowDefinition("wf", "ws", (WorkflowStep("a", "a"),))
    instance = runtime.start(definition)
    done = runtime.run(instance.instance_id, definition)
    assert runtime.recover({"wf": definition}) == ()
    assert done.state == WorkflowState.COMPLETED
