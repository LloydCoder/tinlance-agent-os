"""Agent OS representation of a business Transformation.

Agent OS owns lifecycle/context composition. It does not authorize execution.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal
from uuid import UUID

ExecutionState = Literal["planned", "running", "succeeded", "failed", "cancelled", "partial"]
OutcomeStatus = Literal["unknown", "achieved", "partially_achieved", "not_achieved", "inconclusive"]


@dataclass(frozen=True, slots=True)
class TransformationOutcome:
    status: OutcomeStatus
    achieved: bool

    def __post_init__(self) -> None:
        if self.status == "achieved" and not self.achieved:
            raise ValueError("achieved outcome must set achieved=true")


@dataclass(frozen=True, slots=True)
class TransformationContext:
    workspace_ref: str
    task_ref: str
    source_refs: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.workspace_ref.strip() or not self.task_ref.strip():
            raise ValueError("workspace and task references are required")


@dataclass(frozen=True, slots=True)
class Transformation:
    transformation_id: UUID
    version: int
    tenant_ref: str
    objective: str
    context: TransformationContext
    agent_ref: str
    agent_version: str
    execution_state: ExecutionState = "planned"
    run_ref: str | None = None
    outcome: TransformationOutcome | None = None

    def __post_init__(self) -> None:
        if self.version < 1:
            raise ValueError("transformation version must be >= 1")
        if not self.tenant_ref.strip() or not self.objective.strip():
            raise ValueError("tenant and objective are required")
        if not self.agent_ref.strip() or not self.agent_version.strip():
            raise ValueError("agent identity references are required")

    def with_execution(
        self,
        state: ExecutionState,
        *,
        run_ref: str | None = None,
        outcome: TransformationOutcome | None = None,
    ) -> Transformation:
        return Transformation(
            transformation_id=self.transformation_id,
            version=self.version + 1,
            tenant_ref=self.tenant_ref,
            objective=self.objective,
            context=self.context,
            agent_ref=self.agent_ref,
            agent_version=self.agent_version,
            execution_state=state,
            run_ref=run_ref or self.run_ref,
            outcome=outcome if outcome is not None else self.outcome,
        )
