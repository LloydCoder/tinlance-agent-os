"""Deterministic dependency-aware workflow composition."""

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



@dataclass(slots=True)
class WorkflowEngine:
    def validate(self, definition: WorkflowDefinition) -> None:
        ids = {step.step_id for step in definition.steps}
        if len(ids) != len(definition.steps):
            raise ValueError("duplicate workflow step")
        for step in definition.steps:
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
