"""Durable M16 workflow runtime.

The runtime is a recovery-oriented state machine. Consequential step identity is
stable across retries/restarts and is mapped to the Platform through the supplied
executor; the OS never becomes an authority plane.
"""

from __future__ import annotations

import json
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from hashlib import sha256
from typing import Any, Protocol

from .store import StateStore
from .workflow import (
    WorkflowDefinition,
    WorkflowEngine,
    WorkflowState,
    WorkflowStep,
    WorkflowStepKind,
    WorkflowStepResult,
    WorkflowStepState,
)


class WorkflowRuntimeError(RuntimeError):
    pass


class RetryableWorkflowError(WorkflowRuntimeError):
    pass


class WorkflowCancelled(WorkflowRuntimeError):
    pass


class WorkflowDeadlineExceeded(WorkflowRuntimeError):
    pass


class WorkflowApprovalRequired(WorkflowRuntimeError):
    pass


class WorkflowInputRequired(WorkflowRuntimeError):
    pass


class WorkflowExecutor(Protocol):
    def execute(
        self,
        *,
        workspace_id: str,
        workflow_instance_id: str,
        step: WorkflowStep,
        context: dict[str, Any],
        idempotency_key: str,
        timeout_seconds: float | None,
    ) -> WorkflowStepResult: ...

    def cancel(self, *, platform_run_id: str) -> None: ...

    def request_approval(
        self,
        *,
        workspace_id: str,
        workflow_instance_id: str,
        step: WorkflowStep,
        idempotency_key: str,
    ) -> str: ...

    def compensate(
        self,
        *,
        workspace_id: str,
        workflow_instance_id: str,
        step: WorkflowStep,
        context: dict[str, Any],
        idempotency_key: str,
    ) -> WorkflowStepResult: ...


@dataclass(frozen=True, slots=True)
class WorkflowInstance:
    instance_id: str
    workflow_id: str
    workspace_id: str
    state: WorkflowState
    version: int
    context: dict[str, Any]
    checkpoint: str | None
    deadline_at: datetime | None
    cancel_requested: bool


@dataclass(frozen=True, slots=True)
class WorkflowTrigger:
    trigger_type: str
    trigger_id: str | None = None


@dataclass(frozen=True, slots=True)
class AgentPlatformWorkflowExecutor:
    """Maps workflow consequences to Platform runs; never grants authority locally."""

    platform: Any
    agent_id: str

    def execute(
        self,
        *,
        workspace_id: str,
        workflow_instance_id: str,
        step: WorkflowStep,
        context: dict[str, Any],
        idempotency_key: str,
        timeout_seconds: float | None,
    ) -> WorkflowStepResult:
        run = self.platform.create_run(
            task_id=workflow_instance_id,
            agent_id=self.agent_id,
            intent=step.intent,
            idempotency_key=idempotency_key,
        )
        return WorkflowStepResult(
            WorkflowStepState.COMPLETED,
            output={"workflow_instance_id": workflow_instance_id},
            platform_run_id=run.run_id,
        )

    def cancel(self, *, platform_run_id: str) -> None:
        self.platform.cancel_run(run_id=platform_run_id)

    def request_approval(
        self,
        *,
        workspace_id: str,
        workflow_instance_id: str,
        step: WorkflowStep,
        idempotency_key: str,
    ) -> str:
        anchor = self.platform.create_run(
            task_id=workflow_instance_id,
            agent_id=self.agent_id,
            intent=step.approval_action or step.intent,
            idempotency_key=idempotency_key,
        )
        approval = self.platform.request_approval(
            run_id=anchor.run_id,
            action=step.approval_action or step.intent,
            resource=workflow_instance_id,
            reason="Durable workflow approval gate",
            idempotency_key=idempotency_key,
        )
        return approval.approval_id

    def compensate(
        self,
        *,
        workspace_id: str,
        workflow_instance_id: str,
        step: WorkflowStep,
        context: dict[str, Any],
        idempotency_key: str,
    ) -> WorkflowStepResult:
        run = self.platform.create_run(
            task_id=workflow_instance_id,
            agent_id=self.agent_id,
            intent=f"compensate:{step.intent}",
            idempotency_key=idempotency_key,
        )
        return WorkflowStepResult(
            WorkflowStepState.COMPLETED,
            output={"compensation": step.step_id},
            platform_run_id=run.run_id,
        )


def _now() -> datetime:
    return datetime.now(UTC)


def _json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)


def _step_key(instance_id: str, step_id: str) -> str:
    return sha256(f"workflow:{instance_id}:step:{step_id}".encode()).hexdigest()


def _event_id(instance_id: str, event_type: str, step_id: str | None, payload: Any) -> str:
    return sha256(
        _json({"instance": instance_id, "type": event_type, "step": step_id,
            "payload": payload}).encode()
    ).hexdigest()


class DurableWorkflowRuntime:
    def __init__(
        self,
        store: StateStore,
        executor: WorkflowExecutor,
        *,
        max_parallelism: int = 8,
    ) -> None:
        if max_parallelism < 1:
            raise ValueError("max_parallelism must be positive")
        self.store = store
        self.executor = executor
        self.engine = WorkflowEngine()
        self.max_parallelism = max_parallelism

    def start(
        self,
        definition: WorkflowDefinition,
        *,
        trigger: WorkflowTrigger | None = None,
        context: dict[str, Any] | None = None,
    ) -> WorkflowInstance:
        definition.validate()
        now = _now()
        instance_id = sha256(
            _json({
                "workflow": definition.workflow_id,
                "workspace": definition.workspace_id,
                "trigger": (trigger.trigger_type, trigger.trigger_id) if trigger else ("manual",
                    None),
                "at": now.isoformat(),
            }).encode()
        ).hexdigest()
        deadline = (
            now + timedelta(seconds=definition.deadline_seconds)
            if definition.deadline_seconds is not None else None
        )
        self.store.create_workflow_instance(
            instance_id=instance_id,
            workflow_id=definition.workflow_id,
            workspace_id=definition.workspace_id,
            state=WorkflowState.RUNNING.value,
            trigger_type=trigger.trigger_type if trigger else "manual",
            trigger_id=trigger.trigger_id if trigger else None,
            context=_json(context or {}),
            checkpoint=None,
            deadline_at=deadline.isoformat() if deadline else None,
            created_at=now.isoformat(),
        )
        self._event(instance_id, "workflow.started", None, {"workflow_id": definition.workflow_id})
        for step in definition.steps:
            self.store.upsert_workflow_step(
                instance_id=instance_id,
                step_id=step.step_id,
                state=WorkflowStepState.PENDING.value,
                attempt=0,
                next_attempt_at=None,
                idempotency_key=_step_key(instance_id, step.step_id),
                platform_run_id=None,
                approval_id=None,
                input_data=_json({}),
                output_data=None,
                error=None,
                started_at=None,
                completed_at=None,
                updated_at=now.isoformat(),
            )
        return self.get(instance_id)

    def get(self, instance_id: str) -> WorkflowInstance:
        row = self.store.get_workflow_instance(instance_id)
        if row is None:
            raise WorkflowRuntimeError("workflow instance not found")
        return WorkflowInstance(
            instance_id=row["instance_id"],
            workflow_id=row["workflow_id"],
            workspace_id=row["workspace_id"],
            state=WorkflowState(row["state"]),
            version=int(row["version"]),
            context=json.loads(row["context"]),
            checkpoint=row["checkpoint"],
            deadline_at=datetime.fromisoformat(row["deadline_at"]) if row["deadline_at"] else None,
            cancel_requested=bool(row["cancel_requested"]),
        )

    def run(
        self,
        instance_id: str,
        definition: WorkflowDefinition,
        *,
        wait_for_retry: bool = True,
    ) -> WorkflowInstance:
        definition.validate()
        instance = self.get(instance_id)
        if (
            instance.workflow_id != definition.workflow_id
            or instance.workspace_id != definition.workspace_id
        ):
            raise WorkflowRuntimeError("workflow definition does not match instance")
        while True:
            instance = self.get(instance_id)
            if instance.cancel_requested:
                return self._cancel(instance)
            if instance.deadline_at is not None and _now() >= instance.deadline_at:
                return self._fail(instance, None, "workflow deadline exceeded")
            if instance.state in {
                WorkflowState.COMPLETED, WorkflowState.CANCELLED, WorkflowState.FAILED
            }:
                return instance

            steps = {step.step_id: step for step in definition.steps}
            rows = {row["step_id"]: row for row in self.store.get_workflow_steps(instance_id)}
            completed = {
                step_id for step_id, row in rows.items()
                if row["state"] == WorkflowStepState.COMPLETED.value
            }
            ready = tuple(
                step for step in definition.steps
                if step.step_id not in completed
                and all(
                    rows[dep]["state"] == WorkflowStepState.COMPLETED.value
                    for dep in step.depends_on
                )
                and self._due(rows[step.step_id])
            )
            if not ready:
                if any(row["state"] in {
                    WorkflowStepState.WAITING_APPROVAL.value,
                    WorkflowStepState.WAITING_INPUT.value,
                } for row in rows.values()):
                    return instance
                if all(row["state"] in {
                    WorkflowStepState.COMPLETED.value,
                    WorkflowStepState.COMPENSATED.value,
                    WorkflowStepState.CANCELLED.value,
                } for row in rows.values()):
                    return self._complete(instance)
                if any(
                    row["state"] == WorkflowStepState.RETRY_WAIT.value
                    for row in rows.values()
                ) and wait_for_retry:
                        delays = [
                            max(0.0,
                                (
                                    datetime.fromisoformat(row["next_attempt_at"]) - _now()
                                ).total_seconds()
                            for row in rows.values()
                            if row["state"] == WorkflowStepState.RETRY_WAIT.value
                        ]
                        time.sleep(min(delays, default=0.0))
                        continue
                return instance

            with ThreadPoolExecutor(max_workers=min(self.max_parallelism, len(ready))) as pool:
                futures = {pool.submit(self._run_step, instance_id, steps[step.step_id],
                    instance): step for step in ready}
                results: list[tuple[WorkflowStep, WorkflowStepResult]] = []
                for future, step in futures.items():
                    try:
                        results.append((step, future.result()))
                    except WorkflowCancelled:
                        return self._cancel(self.get(instance_id))
                    except WorkflowApprovalRequired:
                        return self.get(instance_id)
                    except WorkflowInputRequired:
                        return self.get(instance_id)
                    except WorkflowDeadlineExceeded as exc:
                        return self._fail(self.get(instance_id), step.step_id, str(exc))
                    except RetryableWorkflowError as exc:
                        self._retry(instance_id, step, str(exc))
                    except Exception as exc:
                        self._handle_failure(instance_id, definition, step, str(exc))
                        return self.get(instance_id)
            for step, result in results:
                if result.state == WorkflowStepState.COMPLETED:
                    self._complete_step(instance_id, step, result)
                elif result.state == WorkflowStepState.WAITING_APPROVAL:
                    self._wait_approval(instance_id, step, result)
                    return self.get(instance_id)
                elif result.state == WorkflowStepState.WAITING_INPUT:
                    self._wait_input(instance_id, step, result)
                    return self.get(instance_id)
                elif result.state == WorkflowStepState.RETRY_WAIT:
                    self._retry(instance_id, step, result.error or "retry requested")
                elif result.state == WorkflowStepState.FAILED:
                    self._handle_failure(instance_id, definition, step,
                        result.error or "step failed")
                    return self.get(instance_id)

    def resume(self, instance_id: str, definition: WorkflowDefinition) -> WorkflowInstance:
        return self.run(instance_id, definition)

    def cancel(self, instance_id: str, definition: WorkflowDefinition) -> WorkflowInstance:
        instance = self.get(instance_id)
        if instance.workflow_id != definition.workflow_id:
            raise WorkflowRuntimeError("workflow definition does not match instance")
        rows = self.store.get_workflow_steps(instance_id)
        for row in rows:
            if row["platform_run_id"] and row["state"] == WorkflowStepState.RUNNING.value:
                from contextlib import suppress

                with suppress(Exception):
                    self.executor.cancel(platform_run_id=row["platform_run_id"])
        self.store.update_workflow_instance(
            instance_id=instance_id, expected_version=instance.version,
            state=WorkflowState.CANCELLING.value, checkpoint=instance.checkpoint,
            context=_json(instance.context), cancel_requested=True, updated_at=_now().isoformat()
        )
        return self._cancel(self.get(instance_id))

    def provide_input(
        self, instance_id: str, definition: WorkflowDefinition, step_id: str, value: Any
    ) -> WorkflowInstance:
        instance = self.get(instance_id)
        step = next((s for s in definition.steps if s.step_id == step_id), None)
        if step is None or step.kind != WorkflowStepKind.HUMAN_INPUT:
            raise WorkflowRuntimeError("step is not a human-input gate")
        row = next(
            (r for r in self.store.get_workflow_steps(instance_id) if r["step_id"] == step_id),
            None,
        )
        if row is None or row["state"] != WorkflowStepState.WAITING_INPUT.value:
            raise WorkflowRuntimeError("workflow is not waiting for this input")
        context = dict(instance.context)
        context[step.human_input_key or step_id] = value
        self.store.upsert_workflow_step(
            instance_id=instance_id, step_id=step_id, state=WorkflowStepState.COMPLETED.value,
            attempt=int(row["attempt"]),
            next_attempt_at=None,
            idempotency_key=row["idempotency_key"],
            platform_run_id=row["platform_run_id"], approval_id=row["approval_id"],
            input_data=_json(value), output_data=_json(value), error=None,
            started_at=row["started_at"],
            completed_at=_now().isoformat(),
            updated_at=_now().isoformat(),
        )
        self.store.update_workflow_instance(
            instance_id=instance_id, expected_version=instance.version,
            state=WorkflowState.RUNNING.value, checkpoint=step_id, context=_json(context),
            cancel_requested=False, updated_at=_now().isoformat()
        )
        self._event(instance_id, "workflow.input.accepted", step_id, {"key": step.human_input_key})
        return self.run(instance_id, definition)

    def approve(
        self, instance_id: str, definition: WorkflowDefinition, step_id: str, approved: bool
    ) -> WorkflowInstance:
        instance = self.get(instance_id)
        row = next(
            (r for r in self.store.get_workflow_steps(instance_id) if r["step_id"] == step_id),
            None,
        )
        if row is None or row["state"] != WorkflowStepState.WAITING_APPROVAL.value:
            raise WorkflowRuntimeError("workflow is not waiting for this approval")
        if not approved:
            return self._fail(instance, step_id, "approval rejected")
        self.store.upsert_workflow_step(
            instance_id=instance_id, step_id=step_id, state=WorkflowStepState.COMPLETED.value,
            attempt=int(row["attempt"]),
            next_attempt_at=None,
            idempotency_key=row["idempotency_key"],
            platform_run_id=row["platform_run_id"], approval_id=row["approval_id"],
            input_data=row["input_data"], output_data=_json({"approved": True}), error=None,
            started_at=row["started_at"],
            completed_at=_now().isoformat(),
            updated_at=_now().isoformat(),
        )
        self.store.update_workflow_instance(
            instance_id=instance_id, expected_version=instance.version,
            state=WorkflowState.RUNNING.value, checkpoint=step_id, context=instance.context | {},
            cancel_requested=False, updated_at=_now().isoformat()
        )
        self._event(instance_id, "workflow.approval.accepted", step_id,
            {"approval_id": row["approval_id"]})
        return self.run(instance_id, definition)

    def recover(self, definitions: dict[str, WorkflowDefinition]) -> tuple[WorkflowInstance, ...]:
        recovered: list[WorkflowInstance] = []
        for definition in definitions.values():
            # Recovery is deliberately bounded to known definitions supplied by the caller.
            rows = self.store.query(
                "SELECT instance_id FROM workflow_instances WHERE workflow_id=? "
                "AND state NOT IN ('completed','failed','cancelled')",
                (definition.workflow_id,),
            )
            for row in rows:
                instance_id = row["instance_id"]
                for step_row in self.store.get_workflow_steps(instance_id):
                    if step_row["state"] == WorkflowStepState.RUNNING.value:
                        self.store.upsert_workflow_step(
                            instance_id=instance_id,
                            step_id=step_row["step_id"],
                            state=WorkflowStepState.PENDING.value,
                            attempt=int(step_row["attempt"]),
                            next_attempt_at=None,
                            idempotency_key=step_row["idempotency_key"],
                            platform_run_id=step_row["platform_run_id"],
                            approval_id=step_row["approval_id"],
                            input_data=step_row["input_data"],
                            output_data=step_row["output_data"],
                            error="recovered after process interruption",
                            started_at=None,
                            completed_at=None,
                            updated_at=_now().isoformat(),
                        )
                recovered.append(self.resume(instance_id, definition))
        return tuple(recovered)

    def trigger_event(
        self, event_type: str, payload: dict[str, Any], definition: WorkflowDefinition
    ) -> WorkflowInstance:
        return self.start(
            definition,
            trigger=WorkflowTrigger("event", event_type),
            context={"event_type": event_type, "event": payload},
        )

    def schedule(
        self, schedule_id: str, definition: WorkflowDefinition, cron: str, next_run_at: datetime
    ) -> None:
        definition.validate()
        self.store.put_workflow_schedule(
            schedule_id, definition.workflow_id, definition.workspace_id, cron,
            next_run_at.isoformat(), _now().isoformat()
        )

    def fire_due_schedules(
        self, definitions: dict[str, WorkflowDefinition], *, now: datetime | None = None
    ) -> tuple[WorkflowInstance, ...]:
        current = (now or _now()).astimezone(UTC)
        started: list[WorkflowInstance] = []
        for row in self.store.due_workflow_schedules(current.isoformat()):
            definition = definitions.get(row["workflow_id"])
            if definition is None:
                continue
            instance = self.start(
                definition,
                trigger=WorkflowTrigger("schedule", row["schedule_id"]),
                context={"schedule_id": row["schedule_id"], "scheduled_at": row["next_run_at"]},
            )
            started.append(instance)
            # The scheduler owns cadence; the runtime owns durable execution.
            self.store.advance_workflow_schedule(
                row["schedule_id"],
                current.isoformat(),
                current.isoformat(),
            )
        return tuple(started)

    def _run_step(
        self, instance_id: str, step: WorkflowStep, instance: WorkflowInstance
    ) -> WorkflowStepResult:
        if instance.cancel_requested:
            raise WorkflowCancelled()
        if instance.deadline_at is not None and _now() >= instance.deadline_at:
            raise WorkflowDeadlineExceeded("workflow deadline exceeded")
        row = next(
            r for r in self.store.get_workflow_steps(instance_id) if r["step_id"] == step.step_id
        )
        attempt = int(row["attempt"]) + 1
        now = _now().isoformat()
        self.store.upsert_workflow_step(
            instance_id=instance_id, step_id=step.step_id, state=WorkflowStepState.RUNNING.value,
            attempt=attempt, next_attempt_at=None, idempotency_key=row["idempotency_key"],
            platform_run_id=row["platform_run_id"], approval_id=row["approval_id"],
            input_data=_json(instance.context), output_data=row["output_data"], error=None,
            started_at=now, completed_at=None, updated_at=now
        )
        if step.kind == WorkflowStepKind.CONDITION:
            return self._condition(step, instance.context)
        if step.condition is not None and step.kind == WorkflowStepKind.ACTION:
            condition_result = self._condition(step, instance.context)
            if condition_result.output is False:
                return WorkflowStepResult(WorkflowStepState.COMPLETED, {"skipped": True})
        if step.kind == WorkflowStepKind.HUMAN_INPUT:
            return WorkflowStepResult(WorkflowStepState.WAITING_INPUT)
        if step.kind == WorkflowStepKind.APPROVAL:
            approval_id = self.executor.request_approval(
                workspace_id=instance.workspace_id,
                workflow_instance_id=instance_id,
                step=step,
                idempotency_key=row["idempotency_key"],
            )
            return WorkflowStepResult(WorkflowStepState.WAITING_APPROVAL, approval_id=approval_id)
        if step.kind == WorkflowStepKind.COMPENSATION:
            return self.executor.compensate(
                workspace_id=instance.workspace_id,
                workflow_instance_id=instance_id,
                step=step,
                context=instance.context,
                idempotency_key=row["idempotency_key"],
            )
        timeout = step.timeout_seconds
        if step.deadline_seconds is not None:
            timeout = min(timeout,
                step.deadline_seconds) if timeout is not None else step.deadline_seconds
        result = self.executor.execute(
            workspace_id=instance.workspace_id,
            workflow_instance_id=instance_id,
            step=step,
            context=instance.context,
            idempotency_key=row["idempotency_key"],
            timeout_seconds=timeout,
        )
        return result

    @staticmethod
    def _condition(step: WorkflowStep, context: dict[str, Any]) -> WorkflowStepResult:
        expression = (step.condition or "").strip()
        if not expression:
            return WorkflowStepResult(WorkflowStepState.COMPLETED, True)
        if "==" in expression:
            key, expected = (part.strip() for part in expression.split("==", 1))
            actual = context.get(key)
            wanted: Any = expected.strip("'\"")
            return WorkflowStepResult(WorkflowStepState.COMPLETED, actual == wanted)
        if "!=" in expression:
            key, expected = (part.strip() for part in expression.split("!=", 1))
            actual = context.get(key)
            wanted: Any = expected.strip("'\"")
            return WorkflowStepResult(WorkflowStepState.COMPLETED, actual != wanted)
        return WorkflowStepResult(WorkflowStepState.COMPLETED, bool(context.get(expression)))

    def _complete_step(self, instance_id: str, step: WorkflowStep,
        result: WorkflowStepResult) -> None:
        now = _now().isoformat()
        row = next(
            r for r in self.store.get_workflow_steps(instance_id) if r["step_id"] == step.step_id
        )
        self.store.upsert_workflow_step(
            instance_id=instance_id, step_id=step.step_id, state=WorkflowStepState.COMPLETED.value,
            attempt=int(row["attempt"]),
            next_attempt_at=None,
            idempotency_key=row["idempotency_key"],
            platform_run_id=result.platform_run_id, approval_id=result.approval_id,
            input_data=row["input_data"], output_data=_json(result.output),
            error=None, started_at=row["started_at"], completed_at=now, updated_at=now
        )
        instance = self.get(instance_id)
        self.store.update_workflow_instance(
            instance_id=instance_id, expected_version=instance.version,
            state=WorkflowState.CHECKPOINTED.value, checkpoint=step.step_id,
            context=_json(instance.context | {step.step_id: result.output}),
            cancel_requested=False, updated_at=now
        )
        self._event(instance_id, "workflow.step.completed", step.step_id, {
            "attempt": int(row["attempt"]), "platform_run_id": result.platform_run_id
        })

    def _retry(self, instance_id: str, step: WorkflowStep, error: str) -> None:
        row = next(
            r for r in self.store.get_workflow_steps(instance_id) if r["step_id"] == step.step_id
        )
        attempt = int(row["attempt"])
        if attempt >= step.retry.max_attempts:
            self._handle_failure(instance_id, None, step, error)
            return
        due = _now() + timedelta(seconds=step.retry.delay(attempt))
        self.store.upsert_workflow_step(
            instance_id=instance_id, step_id=step.step_id, state=WorkflowStepState.RETRY_WAIT.value,
            attempt=attempt,
            next_attempt_at=due.isoformat(),
            idempotency_key=row["idempotency_key"],
            platform_run_id=row["platform_run_id"], approval_id=row["approval_id"],
            input_data=row["input_data"], output_data=row["output_data"], error=error,
            started_at=row["started_at"], completed_at=None, updated_at=_now().isoformat()
        )
        self._event(instance_id, "workflow.step.retry", step.step_id, {"attempt": attempt,
            "error": error})

    def _handle_failure(
        self, instance_id: str, definition: WorkflowDefinition | None,
        step: WorkflowStep, error: str
    ) -> None:
        row = next(
            r for r in self.store.get_workflow_steps(instance_id) if r["step_id"] == step.step_id
        )
        self.store.upsert_workflow_step(
            instance_id=instance_id, step_id=step.step_id, state=WorkflowStepState.FAILED.value,
            attempt=int(row["attempt"]),
            next_attempt_at=None,
            idempotency_key=row["idempotency_key"],
            platform_run_id=row["platform_run_id"], approval_id=row["approval_id"],
            input_data=row["input_data"], output_data=row["output_data"], error=error,
            started_at=row["started_at"],
            completed_at=_now().isoformat(),
            updated_at=_now().isoformat(),
        )
        self._event(instance_id, "workflow.step.failed", step.step_id, {"error": error})
        instance = self.get(instance_id)
        if definition and definition.compensation_enabled:
            self._compensate(instance_id, definition, instance.context)
        else:
            self._fail(instance, step.step_id, error)

    def _compensate(self, instance_id: str, definition: WorkflowDefinition, context: dict[str,
        Any]) -> None:
        self.store.update_workflow_instance(
            instance_id=instance_id, expected_version=self.get(instance_id).version,
            state=WorkflowState.COMPENSATING.value, checkpoint=self.get(instance_id).checkpoint,
            context=_json(context), cancel_requested=False, updated_at=_now().isoformat()
        )
        completed = {
            row["step_id"] for row in self.store.get_workflow_steps(instance_id)
            if row["state"] == WorkflowStepState.COMPLETED.value
        }
        for step in reversed(definition.steps):
            if step.step_id in completed and step.compensate_with:
                compensation = next(
                    s for s in definition.steps if s.step_id == step.compensate_with
                )
                self._run_step(instance_id, compensation, self.get(instance_id))
                row = next(
                    r
                    for r in self.store.get_workflow_steps(instance_id)
                    if r["step_id"] == compensation.step_id
                )
                self.store.upsert_workflow_step(
                    instance_id=instance_id, step_id=compensation.step_id,
                    state=WorkflowStepState.COMPENSATED.value, attempt=int(row["attempt"]),
                    next_attempt_at=None, idempotency_key=row["idempotency_key"],
                    platform_run_id=row["platform_run_id"], approval_id=row["approval_id"],
                    input_data=row["input_data"], output_data=row["output_data"], error=None,
                    started_at=row["started_at"],
            completed_at=_now().isoformat(),
            updated_at=_now().isoformat(),
                )
        self._fail(self.get(instance_id), None, "workflow failed after compensation")

    def _wait_approval(
        self, instance_id: str, step: WorkflowStep,
        result: WorkflowStepResult) -> None:
        row = next(
            r for r in self.store.get_workflow_steps(instance_id) if r["step_id"] == step.step_id
        )
        self.store.upsert_workflow_step(
            instance_id=instance_id,
            step_id=step.step_id,
            state=WorkflowStepState.WAITING_APPROVAL.value,
            attempt=int(row["attempt"]),
            next_attempt_at=None,
            idempotency_key=row["idempotency_key"],
            platform_run_id=result.platform_run_id, approval_id=result.approval_id,
            input_data=row["input_data"], output_data=None, error=None,
            started_at=row["started_at"], completed_at=None, updated_at=_now().isoformat()
        )
        instance = self.get(instance_id)
        self.store.update_workflow_instance(
            instance_id=instance_id, expected_version=instance.version,
            state=WorkflowState.WAITING_APPROVAL.value, checkpoint=step.step_id,
            context=_json(instance.context), cancel_requested=False, updated_at=_now().isoformat()
        )
        self._event(instance_id, "workflow.approval.requested", step.step_id,
            {"approval_id": result.approval_id})

    def _wait_input(
        self, instance_id: str, step: WorkflowStep, result: WorkflowStepResult
    ) -> None:
        row = next(
            r for r in self.store.get_workflow_steps(instance_id) if r["step_id"] == step.step_id
        )
        self.store.upsert_workflow_step(
            instance_id=instance_id,
            step_id=step.step_id,
            state=WorkflowStepState.WAITING_INPUT.value,
            attempt=int(row["attempt"]),
            next_attempt_at=None,
            idempotency_key=row["idempotency_key"],
            platform_run_id=result.platform_run_id, approval_id=result.approval_id,
            input_data=row["input_data"], output_data=None, error=None,
            started_at=row["started_at"], completed_at=None, updated_at=_now().isoformat()
        )
        instance = self.get(instance_id)
        self.store.update_workflow_instance(
            instance_id=instance_id, expected_version=instance.version,
            state=WorkflowState.WAITING_INPUT.value, checkpoint=step.step_id,
            context=_json(instance.context), cancel_requested=False, updated_at=_now().isoformat()
        )
        self._event(instance_id, "workflow.input.requested", step.step_id,
            {"key": step.human_input_key})

    def _complete(self, instance: WorkflowInstance) -> WorkflowInstance:
        self.store.update_workflow_instance(
            instance_id=instance.instance_id, expected_version=instance.version,
            state=WorkflowState.COMPLETED.value, checkpoint=instance.checkpoint,
            context=_json(instance.context), cancel_requested=False, updated_at=_now().isoformat()
        )
        self._event(instance.instance_id, "workflow.completed", None, {})
        return self.get(instance.instance_id)

    def _cancel(self, instance: WorkflowInstance) -> WorkflowInstance:
        current = self.get(instance.instance_id)
        if current.state != WorkflowState.CANCELLED:
            self.store.update_workflow_instance(
                instance_id=current.instance_id, expected_version=current.version,
                state=WorkflowState.CANCELLED.value, checkpoint=current.checkpoint,
                context=_json(current.context), cancel_requested=True, updated_at=_now().isoformat()
            )
            self._event(current.instance_id, "workflow.cancelled", None, {})
        return self.get(instance.instance_id)

    def _fail(self, instance: WorkflowInstance, step_id: str | None,
        error: str) -> WorkflowInstance:
        current = self.get(instance.instance_id)
        if current.state != WorkflowState.FAILED:
            self.store.update_workflow_instance(
                instance_id=current.instance_id, expected_version=current.version,
                state=WorkflowState.FAILED.value, checkpoint=step_id or current.checkpoint,
                context=_json(current.context | {"_error": error}), cancel_requested=False,
                updated_at=_now().isoformat()
            )
            self._event(current.instance_id, "workflow.failed", step_id, {"error": error})
        return self.get(instance.instance_id)

    def _due(self, row: Any) -> bool:
        if row["state"] == WorkflowStepState.RETRY_WAIT.value:
            return (
                row["next_attempt_at"] is not None
                and datetime.fromisoformat(row["next_attempt_at"]) <= _now()
            )
        return row["state"] in {WorkflowStepState.PENDING.value, WorkflowStepState.READY.value}

    def _event(self, instance_id: str, event_type: str, step_id: str | None, payload: Any) -> None:
        self.store.append_workflow_event(
            event_id=_event_id(instance_id, event_type, step_id, payload),
            instance_id=instance_id,
            event_type=event_type,
            step_id=step_id,
            occurred_at=_now().isoformat(),
            payload=_json(payload),
        )
