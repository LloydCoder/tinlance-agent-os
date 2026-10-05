"""Versioned, authority-neutral Agent Catalog v2 profile contract."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


class RiskLevel(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class AutonomyLevel(StrEnum):
    ASSISTED = "assisted"
    SUPERVISED = "supervised"
    BOUNDED = "bounded"
    AUTONOMOUS = "autonomous"


@dataclass(frozen=True, slots=True)
class CapabilityProfile:
    id: str
    version: str
    domain: str
    capability_ids: tuple[str, ...]
    skill_ids: tuple[str, ...] = ()
    inputs: tuple[str, ...] = ()
    outputs: tuple[str, ...] = ()
    tools: tuple[str, ...] = ()
    environments: tuple[str, ...] = ()
    modalities: tuple[str, ...] = ()
    protocols: tuple[str, ...] = ()
    models: tuple[str, ...] = ()
    risk_level: RiskLevel = RiskLevel.LOW
    autonomy_level: AutonomyLevel = AutonomyLevel.SUPERVISED
    approval_policy: str = "platform-default"
    data_sensitivity: str = "internal"
    delegation_allowed: bool = False
    max_delegation_depth: int = 0
    max_fanout: int = 0
    evidence_required: bool = True
    evaluation_suite: str = "default"
    provenance: tuple[str, ...] = ()
    compatibility: dict[str, str] = field(default_factory=dict)
    status: str = "active"

    def __post_init__(self) -> None:
        if not self.id.strip() or not self.version.strip() or not self.domain.strip():
            raise ValueError("profile id, version and domain are required")
        if not self.capability_ids:
            raise ValueError("at least one capability is required")
        if self.max_delegation_depth < 0 or self.max_fanout < 0:
            raise ValueError("delegation limits cannot be negative")
        if not self.delegation_allowed and (self.max_delegation_depth or self.max_fanout):
            raise ValueError("delegation limits require delegation_allowed=true")
        if not self.provenance:
            raise ValueError("profile provenance is required")

    def to_record(self) -> dict[str, Any]:
        result = {
            "schema": "tinlance.agent-profile.v2",
            "id": self.id,
            "version": self.version,
            "domain": self.domain,
            "capabilities": list(self.capability_ids),
            "skills": list(self.skill_ids),
            "inputs": list(self.inputs),
            "outputs": list(self.outputs),
            "tools": list(self.tools),
            "environments": list(self.environments),
            "modalities": list(self.modalities),
            "protocols": list(self.protocols),
            "models": list(self.models),
            "risk_level": self.risk_level.value,
            "autonomy_level": self.autonomy_level.value,
            "approval_policy": self.approval_policy,
            "data_sensitivity": self.data_sensitivity,
            "delegation_allowed": self.delegation_allowed,
            "max_delegation_depth": self.max_delegation_depth,
            "max_fanout": self.max_fanout,
            "evidence_required": self.evidence_required,
            "evaluation_suite": self.evaluation_suite,
            "provenance": list(self.provenance),
            "compatibility": dict(self.compatibility),
            "status": self.status,
        }
        return result
