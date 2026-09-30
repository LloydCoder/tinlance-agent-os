"""Deterministic workflow contracts and validation for the durable M16 runtime."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


class WorkflowState(StrEnum):
    CREATED = "created"
    RUNNING = "running"
    WAITING_INPUT = "waiting_input"
    WAITING_APPROVAL = "waiting_approval"
    CHECKPOINTED = "checkpointed"
    CANCELLING = "cancelling"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    COMPENSATING = "compensating"


class WorkflowStepState(StrEnum):
    PENDING = "pending"
    READY = "ready"
    RUNNING = "running"
    WAITING_INPUT = "waiting_input"
    WAITING_APPROVAL = "waiting_approval"
    RETRY_WAIT = "retry_wait"
    COMPLETED = "completed"
    FAILED = "failed"
    COMPENSATED = "compensated"
    CANCELLED = "cancelled"


class WorkflowStepKind(StrEnum):
    ACTION = "action"
    APPROVAL = "approval"
    HUMAN_INPUT = "human_input"
    CONDITION = "condition"
    COMPENSATION = "compensation"


class RetryPolicy:
    __slots__ = ("max_attempts", "backoff_seconds", "max_backoff_seconds")

    def __init__(self, max_attempts: int = 1, backoff_seconds: float = 0.0, max_backoff_seconds: float = 300.0) -> None:
        if max_attempts < 1:
            raise ValueError("max_attempts must be positive")
        if backoff_seconds < 0 or max_backoff_seconds < 0:
            raise ValueError("backoff values cannot be negative")
        self.max_attempts = max_attempts
        self.backoff_seconds = backoff_seconds
        self.max_backoff_seconds = max_backoff_seconds

    def delay(self, attempt: int) -> float:
        return min(self.max_backoff_seconds, self.backoff_seconds * (2 ** max(0, attempt - 1)))


@dataclass(frozen=True, slots=True)
class WorkflowStep:
    step_id: str
    intent: str
    depends_on: tuple[str, ...] = ()
    kind: WorkflowStepKind = WorkflowStepKind.ACTION
    condition: str | None = None
    retry: RetryPolicy = field(default_factory=RetryPolicy)
    timeout_seconds: float | None = None
    deadline_seconds: float | None = None
    approval_action: str | None = None
    human_input_key: str | None = None
    compensate_with: str | None = None
    consequential: bool = True

    def validate(self) -> None:
        if not self.step_id.strip() or not self.intent.strip():
            raise ValueError("workflow steps require an id and intent")
        if len(self.depends_on) != len(set(self.depends_on)):
            raise ValueError("workflow step has duplicate dependencies")
        if self.step_id in self.depends_on:
            raise ValueError("workflow step cannot depend on itself")
        if self.timeout_seconds is not None and self.timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive")
        if self.deadline_seconds is not None and self.deadline_seconds <= 0:
            raise ValueError("deadline_seconds must be positive")
        if self.kind == WorkflowStepKind.APPROVAL and not (self.approval_action or self.intent):
            raise ValueError("approval steps require an action")
        if self.kind == WorkflowStepKind.HUMAN_INPUT and not self.human_input_key:
            raise ValueError("human-input steps require human_input_key")


@dataclass(frozen=True, slots=True)
class WorkflowDefinition:
    workflow_id: str
    workspace_id: str
    steps: tuple[WorkflowStep, ...]
    deadline_seconds: float | None = None
    compensation_enabled: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)

    def validate(self) -> None:
        if not self.workflow_id.strip() or not self.workspace_id.strip():
            raise ValueError("workflow_id and workspace_id are required")
        if self.deadline_seconds is not None and self.deadline_seconds <= 0:
            raise ValueError("workflow deadline must be positive")
        ids = {step.step_id for step in self.steps}
        if len(ids) != len(self.steps):
            raise ValueError("duplicate workflow step")
        for step in self.steps:
            step.validate()
            if any(dependency not in ids for dependency in step.depends_on):
                raise ValueError("workflow dependency references an unknown step")
            if step.compensate_with is not None and step.compensate_with not in ids:
                raise ValueError("compensation references an unknown step")
        graph = {step.step_id: set(step.depends_on) for step in self.steps}
        while graph:
            ready = {key for key, value in graph.items() if not value}
            if not ready:
                raise ValueError("workflow dependency cycle")
            for key in ready:
                del graph[key]
            for dependencies in graph.values():
                dependencies.difference_update(ready)


@dataclass(frozen=True, slots=True)
class WorkflowExecution:
    workflow_id: str
    state: WorkflowState
    completed: frozenset[str] = frozenset()
    failed_step: str | None = None
    checkpoint: str | None = None
    outputs: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class WorkflowStepResult:
    state: WorkflowStepState
    output: Any = None
    platform_run_id: str | None = None
    approval_id: str | None = None
    error: str | None = None


@dataclass(slots=True)
class WorkflowEngine:
    def validate(self, definition: WorkflowDefinition) -> None:
        definition.validate()

    def start(self, definition: WorkflowDefinition) -> WorkflowExecution:
        self.validate(definition)
        if not definition.steps:
            return WorkflowExecution(definition.workflow_id, WorkflowState.COMPLETED)
        return WorkflowExecution(definition.workflow_id, WorkflowState.RUNNING)

    def ready_steps(
        self,
        definition: WorkflowDefinition,
        completed: set[str],
    ) -> tuple[WorkflowStep, ...]:
        self.validate(definition)
        known = {step.step_id for step in definition.steps}
        if not completed <= known:
            raise ValueError("completed set contains an unknown step")
        return tuple(
            step for step in definition.steps
            if step.step_id not in completed and set(step.depends_on) <= completed
        )

    def complete_step(
        self, definition: WorkflowDefinition, execution: WorkflowExecution, step_id: str,
    ) -> WorkflowExecution:
        self.validate(definition)
        if execution.workflow_id != definition.workflow_id:
            raise ValueError("execution does not belong to workflow")
        if execution.state not in {
            WorkflowState.RUNNING, WorkflowState.WAITING_INPUT,
            WorkflowState.WAITING_APPROVAL, WorkflowState.CHECKPOINTED,
        }:
            raise ValueError("workflow is not executable")
        ready = self.ready_steps(definition, set(execution.completed))
        if step_id not in {step.step_id for step in ready}:
            raise ValueError("workflow step is not ready")
        completed = frozenset((*execution.completed, step_id))
        state = WorkflowState.COMPLETED if len(completed) == len(definition.steps) else WorkflowState.RUNNING
        return WorkflowExecution(
            definition.workflow_id, state, completed, outputs=execution.outputs
        )

    def fail_step(
        self, definition: WorkflowDefinition, execution: WorkflowExecution, step_id: str,
    ) -> WorkflowExecution:
        self.validate(definition)
        if execution.workflow_id != definition.workflow_id:
            raise ValueError("execution does not belong to workflow")
        if step_id not in {step.step_id for step in definition.steps}:
            raise ValueError("unknown workflow step")
        return WorkflowExecution(
            definition.workflow_id, WorkflowState.FAILED, execution.completed,
            failed_step=step_id, checkpoint=execution.checkpoint, outputs=execution.outputs
        )

    def cancel(self, definition: WorkflowDefinition, execution: WorkflowExecution) -> WorkflowExecution:
        self.validate(definition)
        if execution.workflow_id != definition.workflow_id:
            raise ValueError("execution does not belong to workflow")
        return WorkflowExecution(
            definition.workflow_id, WorkflowState.CANCELLED, execution.completed,
            execution.failed_step, execution.checkpoint, execution.outputs
        )
