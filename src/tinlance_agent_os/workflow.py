"""Deterministic dependency-aware workflow composition and lifecycle."""

from dataclasses import dataclass
from enum import StrEnum


class WorkflowState(StrEnum):
    CREATED = "created"
    RUNNING = "running"
    WAITING_INPUT = "waiting_input"
    WAITING_APPROVAL = "waiting_approval"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass(frozen=True, slots=True)
class WorkflowStep:
    step_id: str
    intent: str
    depends_on: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class WorkflowDefinition:
    workflow_id: str
    workspace_id: str
    steps: tuple[WorkflowStep, ...]


@dataclass(frozen=True, slots=True)
class WorkflowExecution:
    workflow_id: str
    state: WorkflowState
    completed: frozenset[str] = frozenset()
    failed_step: str | None = None


@dataclass(slots=True)
class WorkflowEngine:
    def validate(self, definition: WorkflowDefinition) -> None:
        if not definition.workflow_id.strip() or not definition.workspace_id.strip():
            raise ValueError("workflow_id and workspace_id are required")
        ids = {step.step_id for step in definition.steps}
        if len(ids) != len(definition.steps):
            raise ValueError("duplicate workflow step")
        for step in definition.steps:
            if not step.step_id.strip() or not step.intent.strip():
                raise ValueError("workflow steps require an id and intent")
            if len(step.depends_on) != len(set(step.depends_on)):
                raise ValueError("workflow step has duplicate dependencies")
            if step.step_id in step.depends_on:
                raise ValueError("workflow step cannot depend on itself")
            if any(dependency not in ids for dependency in step.depends_on):
                raise ValueError("workflow dependency references an unknown step")
        graph = {step.step_id: set(step.depends_on) for step in definition.steps}
        while graph:
            ready = {key for key, value in graph.items() if not value}
            if not ready:
                raise ValueError("workflow dependency cycle")
            for key in ready:
                del graph[key]
            for dependencies in graph.values():
                dependencies.difference_update(ready)

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
            step
            for step in definition.steps
            if step.step_id not in completed and set(step.depends_on) <= completed
        )

    def complete_step(
        self,
        definition: WorkflowDefinition,
        execution: WorkflowExecution,
        step_id: str,
    ) -> WorkflowExecution:
        self.validate(definition)
        if execution.workflow_id != definition.workflow_id:
            raise ValueError("execution does not belong to workflow")
        if execution.state not in {WorkflowState.RUNNING, WorkflowState.WAITING_INPUT, WorkflowState.WAITING_APPROVAL}:
            raise ValueError("workflow is not executable")
        if step_id not in {step.step_id for step in definition.steps}:
            raise ValueError("unknown workflow step")
        if step_id not in {step.step_id for step in self.ready_steps(definition, set(execution.completed))}:
            raise ValueError("workflow step is not ready")
        completed = frozenset((*execution.completed, step_id))
        state = (
            WorkflowState.COMPLETED
            if len(completed) == len(definition.steps)
            else WorkflowState.RUNNING
        )
        return WorkflowExecution(definition.workflow_id, state, completed)

    def fail_step(
        self,
        definition: WorkflowDefinition,
        execution: WorkflowExecution,
        step_id: str,
    ) -> WorkflowExecution:
        self.validate(definition)
        if execution.workflow_id != definition.workflow_id:
            raise ValueError("execution does not belong to workflow")
        if step_id not in {step.step_id for step in definition.steps}:
            raise ValueError("unknown workflow step")
        return WorkflowExecution(
            definition.workflow_id,
            WorkflowState.FAILED,
            execution.completed,
            failed_step=step_id,
        )

    def cancel(self, definition: WorkflowDefinition, execution: WorkflowExecution) -> WorkflowExecution:
        self.validate(definition)
        if execution.workflow_id != definition.workflow_id:
            raise ValueError("execution does not belong to workflow")
        return WorkflowExecution(
            definition.workflow_id,
            WorkflowState.CANCELLED,
            execution.completed,
            execution.failed_step,
        )
