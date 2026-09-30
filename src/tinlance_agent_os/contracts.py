"""Stable OS-facing protocols and integration contracts."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol

from .domain import (
    Agent,
    ApprovalRef,
    CapabilityRef,
    Event,
    EvidenceRef,
    PlatformRunRef,
    User,
)


class AgentPlatformClient(Protocol):
    """Authority-preserving boundary to Tinlance Agent Platform.

    Implementations transport requests and references only. They must not
    reproduce Platform authorization, policy, approval, sandbox, or evidence
    authority locally.
    """

    def get_principal(self) -> User: ...

    def list_agents(self) -> Sequence[Agent]: ...

    def create_run(
        self,
        *,
        task_id: str,
        agent_id: str,
        intent: str,
        idempotency_key: str | None = None,
    ) -> PlatformRunRef: ...

    def cancel_run(self, *, run_id: str) -> PlatformRunRef: ...

    def list_capabilities(self, *, agent_id: str) -> Sequence[CapabilityRef]: ...

    def request_approval(
        self,
        *,
        run_id: str,
        action: str,
        resource: str | None = None,
        reason: str | None = None,
        idempotency_key: str | None = None,
    ) -> ApprovalRef: ...

    def get_events(self, *, run_id: str) -> Sequence[Event]: ...

    def get_evidence(self, *, run_id: str) -> Sequence[EvidenceRef]: ...

    def health(self) -> bool: ...
