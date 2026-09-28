"""Deterministic dependency-aware workflow composition."""
from __future__ import annotations
from dataclasses import dataclass
from enum import StrEnum
from collections.abc import Mapping, Sequence
from uuid import uuid4
from .domain import Task, TaskState

class WorkflowState(StrEnum):
    CREATED="created"; RUNNING="running"; WAITING_INPUT="waiting_input"; WAITING_APPROVAL="waiting_approval"; COMPLETED="completed"; FAILED="failed"; CANCELLED="cancelled"

@dataclass(frozen=True, slots=True)
class WorkflowStep:
    step_id: str
    intent: str
    depends_on: tuple[str,...]=()

@dataclass(frozen=True, slots=True)
class WorkflowDefinition:
    workflow_id: str
    workspace_id: str
    steps: tuple[WorkflowStep,...]

@dataclass(slots=True)
class WorkflowEngine:
    def validate(self, definition: WorkflowDefinition) -> None:
        ids={s.step_id for s in definition.steps}
        if len(ids)!=len(definition.steps): raise ValueError("duplicate workflow step")
        for step in definition.steps:
            if step.step_id in step.depends_on or any(x not in ids for x in step.depends_on): raise ValueError("invalid workflow dependency")
        graph={s.step_id:set(s.depends_on) for s in definition.steps}; seen=set()
        while graph:
            ready={k for k,v in graph.items() if not v}
            if not ready: raise ValueError("workflow dependency cycle")
            seen |= ready
            for k in list(graph):
                graph[k]-=ready
                if k in ready: del graph[k]
    def ready_steps(self, definition: WorkflowDefinition, completed: set[str]) -> tuple[WorkflowStep,...]:
        self.validate(definition)
        return tuple(s for s in definition.steps if s.step_id not in completed and set(s.depends_on)<=completed)
