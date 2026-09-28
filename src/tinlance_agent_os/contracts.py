"""Stable OS-facing protocols and integration contracts."""

from __future__ import annotations

from typing import Protocol, Sequence

from .domain import (
    Agent,
    ApprovalRef,
    CapabilityRef,
    EvidenceRef,
    Event,
    PlatformRunRef,
    User,
)


class AgentPlatformClient(Protocol):
    """Minimal authority-preserving boundary to Tinlance Agent Platform.

    Implementations may use HTTP, RPC, or another transport. They must not
    reproduce Platform authorization logic locally.
    """

    def get_principal(self) -> User: ...

    def list_agents(self) -> Sequence[Agent]: ...

    def create_run(self, *, task_id: str, agent_id: str, intent: str) -> PlatformRunRef: ...

    def cancel_run(self, *, run_id: str) -> PlatformRunRef: ...

    def list_capabilities(self, *, agent_id: str) -> Sequence[CapabilityRef]: ...

    def request_approval(self, *, run_id: str, action: str) -> ApprovalRef: ...

    def get_events(self, *, run_id: str) -> Sequence[Event]: ...

    def get_evidence(self, *, run_id: str) -> Sequence[EvidenceRef]: ...

    def health(self) -> bool: ...
