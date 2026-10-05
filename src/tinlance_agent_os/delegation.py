"""Authority-neutral delegation proposal; Platform remains admission authority."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class DelegationEnvelope:
    parent_agent: str
    child_agent: str
    tenant_id: str
    workspace_id: str
    capabilities: tuple[str, ...]
    max_depth: int
    max_fanout: int
    budget_tokens: int
    budget_cost_microunits: int

    def __post_init__(self) -> None:
        if not self.parent_agent or not self.child_agent:
            raise ValueError("parent and child agents are required")
        if not self.tenant_id or not self.workspace_id:
            raise ValueError("tenant and workspace are required")
        limits = (
            self.max_depth,
            self.max_fanout,
            self.budget_tokens,
            self.budget_cost_microunits,
        )
        if min(limits) < 0:
            raise ValueError("delegation limits cannot be negative")
        if not self.capabilities:
            raise ValueError("delegation capabilities are required")

    def attenuated_from(self, parent: DelegationEnvelope) -> bool:
        return (
            self.parent_agent == parent.child_agent
            and self.tenant_id == parent.tenant_id
            and self.workspace_id == parent.workspace_id
            and set(self.capabilities).issubset(parent.capabilities)
            and self.max_depth <= parent.max_depth
            and self.max_fanout <= parent.max_fanout
            and self.budget_tokens <= parent.budget_tokens
            and self.budget_cost_microunits <= parent.budget_cost_microunits
        )
