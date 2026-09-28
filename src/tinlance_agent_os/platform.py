"""Provider-neutral interface to the Tinlance Agent Platform."""

from dataclasses import dataclass
from typing import Protocol

from .domain import Agent, CorrelationId, Event, RunId, Task


@dataclass(frozen=True, slots=True)
class PlatformRun:
    run_id: RunId
    correlation_id: CorrelationId
    status: str


@dataclass(frozen=True, slots=True)
class PlatformEvidenceRef:
    evidence_id: str
    run_id: RunId
    uri: str | None = None


class AgentPlatformClient(Protocol):
    """Only stable platform operations required by Agent OS.

    Implementations must call the Agent Platform public contract/API.
    They must not import Agent Platform internal packages.
    """

    def list_agents(self) -> tuple[Agent, ...]: ...
    def start_run(self, task: Task) -> PlatformRun: ...
    def cancel_run(self, run_id: RunId) -> None: ...
    def get_run(self, run_id: RunId) -> PlatformRun: ...
    def get_events(self, correlation_id: CorrelationId) -> tuple[Event, ...]: ...
    def get_evidence(self, run_id: RunId) -> tuple[PlatformEvidenceRef, ...]: ...
