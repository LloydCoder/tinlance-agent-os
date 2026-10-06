"""Descriptive security/trust classification for Agent Catalog v3.

Classification is metadata for discovery, evaluation, and risk-aware selection.
It never grants authority. Platform remains the sole authority for admission,
authorization, approval, execution, and delegation.
"""
from __future__ import annotations
import hashlib
import json
from dataclasses import dataclass
from enum import StrEnum

class RiskClass(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class AutonomyClass(StrEnum):
    ASSISTED = "assisted"
    SUPERVISED = "supervised"
    CONDITIONAL = "conditional"
    AUTONOMOUS = "autonomous"

class DataSensitivity(StrEnum):
    PUBLIC = "public"
    INTERNAL = "internal"
    CONFIDENTIAL = "confidential"
    RESTRICTED = "restricted"

@dataclass(frozen=True, slots=True)
class SecurityTrustProfile:
    risk_class: RiskClass
    autonomy_class: AutonomyClass
    data_sensitivity: DataSensitivity
    write_capable: bool
    network_access: bool
    credential_required: bool
    destructive_action_potential: bool
    human_approval_required: bool
    evidence_required: bool
    isolation_required: bool

    def __post_init__(self) -> None:
        if self.destructive_action_potential and self.risk_class is RiskClass.LOW:
            raise ValueError("destructive actions cannot be classified as low risk")
        if self.data_sensitivity is DataSensitivity.RESTRICTED and self.risk_class is RiskClass.LOW:
            raise ValueError("restricted data cannot be classified as low risk")
        if self.autonomy_class is AutonomyClass.AUTONOMOUS and not self.evidence_required:
            raise ValueError("autonomous profiles require evidence")
        if self.destructive_action_potential and not self.human_approval_required:
            raise ValueError("destructive actions require human approval metadata")
        if self.credential_required and not self.network_access:
            raise ValueError("credential requirement requires network access metadata")
        if (
            self.risk_class in {RiskClass.HIGH, RiskClass.CRITICAL}
            and not self.isolation_required
        ):
            raise ValueError("high and critical risk profiles require isolation metadata")

    @property
    def fingerprint(self) -> str:
        payload = {
            "risk_class": self.risk_class.value,
            "autonomy_class": self.autonomy_class.value,
            "data_sensitivity": self.data_sensitivity.value,
            "write_capable": self.write_capable,
            "network_access": self.network_access,
            "credential_required": self.credential_required,
            "destructive_action_potential": self.destructive_action_potential,
            "human_approval_required": self.human_approval_required,
            "evidence_required": self.evidence_required,
            "isolation_required": self.isolation_required,
        }
        encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()

def classify_security_trust(**kwargs: object) -> SecurityTrustProfile:
    return SecurityTrustProfile(**kwargs)
