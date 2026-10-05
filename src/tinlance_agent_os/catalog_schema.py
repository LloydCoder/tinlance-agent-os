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
    evaluation_score: float = 0.0
    trust_score: float = 0.0
    cost_microunits: int = 0
    latency_ms: int = 0
    provenance: tuple[str, ...] = ()
    artifact_digest: str = ""
    signature_ref: str = ""
    sbom_ref: str = ""
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
        if not 0.0 <= self.evaluation_score <= 1.0:
            raise ValueError("evaluation_score must be between 0 and 1")
        if not 0.0 <= self.trust_score <= 1.0:
            raise ValueError("trust_score must be between 0 and 1")
        if self.cost_microunits < 0 or self.latency_ms < 0:
            raise ValueError("cost and latency cannot be negative")

    def to_record(self) -> dict[str, Any]:
        return {
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
            "evaluation_score": self.evaluation_score,
            "trust_score": self.trust_score,
            "cost_microunits": self.cost_microunits,
            "latency_ms": self.latency_ms,
            "provenance": list(self.provenance),
            "artifact_digest": self.artifact_digest,
            "signature_ref": self.signature_ref,
            "sbom_ref": self.sbom_ref,
            "compatibility": dict(self.compatibility),
            "status": self.status,
        }

    @classmethod
    def from_record(cls, record: dict[str, Any]) -> CapabilityProfile:
        if record.get("schema") != "tinlance.agent-profile.v2":
            raise ValueError("unsupported profile schema")
        return cls(
            id=str(record["id"]),
            version=str(record["version"]),
            domain=str(record["domain"]),
            capability_ids=tuple(record["capabilities"]),
            skill_ids=tuple(record.get("skills", ())),
            inputs=tuple(record.get("inputs", ())),
            outputs=tuple(record.get("outputs", ())),
            tools=tuple(record.get("tools", ())),
            environments=tuple(record.get("environments", ())),
            modalities=tuple(record.get("modalities", ())),
            protocols=tuple(record.get("protocols", ())),
            models=tuple(record.get("models", ())),
            risk_level=RiskLevel(record.get("risk_level", RiskLevel.LOW)),
            autonomy_level=AutonomyLevel(record.get("autonomy_level", AutonomyLevel.SUPERVISED)),
            approval_policy=str(record.get("approval_policy", "platform-default")),
            data_sensitivity=str(record.get("data_sensitivity", "internal")),
            delegation_allowed=bool(record.get("delegation_allowed", False)),
            max_delegation_depth=int(record.get("max_delegation_depth", 0)),
            max_fanout=int(record.get("max_fanout", 0)),
            evidence_required=bool(record.get("evidence_required", True)),
            evaluation_suite=str(record.get("evaluation_suite", "default")),
            evaluation_score=float(record.get("evaluation_score", 0.0)),
            trust_score=float(record.get("trust_score", 0.0)),
            cost_microunits=int(record.get("cost_microunits", 0)),
            latency_ms=int(record.get("latency_ms", 0)),
            provenance=tuple(record.get("provenance", ())),
            artifact_digest=str(record.get("artifact_digest", "")),
            signature_ref=str(record.get("signature_ref", "")),
            sbom_ref=str(record.get("sbom_ref", "")),
            compatibility=dict(record.get("compatibility", {})),
            status=str(record.get("status", "active")),
        )
