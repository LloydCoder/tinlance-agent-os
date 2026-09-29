"""Provider-neutral Agent Platform client boundary.

M0 deliberately ships a deterministic reference client for contract testing.
It is not an authority engine and performs no authorization decisions.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from uuid import uuid4

from .contracts import AgentPlatformClient
from .domain import (
    Agent,
    ApprovalRef,
    CapabilityRef,
    Event,
    EvidenceRef,
    PlatformRunRef,
    TaskState,
    User,
)


@dataclass
class ReferenceAgentPlatformClient(AgentPlatformClient):
    """In-process conformance double for the Agent Platform boundary."""

    principal: User = field(default_factory=lambda: User("reference-user"))
    agents: list[Agent] = field(default_factory=list)
    runs: dict[str, PlatformRunRef] = field(default_factory=dict)
    events: dict[str, list[Event]] = field(default_factory=dict)

    def get_principal(self) -> User:
        return self.principal

    def list_agents(self) -> Sequence[Agent]:
        return tuple(self.agents)

    def create_run(self, *, task_id: str, agent_id: str, intent: str) -> PlatformRunRef:
        if not task_id or not agent_id or not intent:
            raise ValueError("task_id, agent_id and intent are required")
        run = PlatformRunRef(str(uuid4()), task_id, TaskState.RUNNING.value)
        self.runs[run.run_id] = run
        return run

    def cancel_run(self, *, run_id: str) -> PlatformRunRef:
        current = self.runs[run_id]
        cancelled = PlatformRunRef(current.run_id, current.task_id, TaskState.CANCELLED.value)
        self.runs[run_id] = cancelled
        return cancelled

    def list_capabilities(self, *, agent_id: str) -> Sequence[CapabilityRef]:
        return (CapabilityRef(f"agent:{agent_id}:capabilities"),)

    def request_approval(
        self,
        *,
        run_id: str,
        action: str,
        resource: str | None = None,
        reason: str | None = None,
    ) -> ApprovalRef:
        if not run_id or not action:
            raise ValueError("run_id and action are required")
        return ApprovalRef(f"approval:{run_id}:{action}")

    def get_events(self, *, run_id: str) -> Sequence[Event]:
        return tuple(self.events.get(run_id, ()))

    def get_evidence(self, *, run_id: str) -> Sequence[EvidenceRef]:
        return (EvidenceRef(f"evidence:{run_id}"),)

    def health(self) -> bool:
        return True
