"""Canonical Agent Catalog v2 semantic ontology.

Ontology metadata is descriptive and planning-only. It never grants Platform
authority, changes policy, approves actions, or executes work.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class OntologyKind(StrEnum):
    DOMAIN = "domain"
    CAPABILITY_FAMILY = "capability_family"
    CAPABILITY = "capability"
    SKILL = "skill"
    ROLE = "role"
    ARCHETYPE = "archetype"
    TOOL = "tool"
    ENVIRONMENT = "environment"
    PROTOCOL = "protocol"


@dataclass(frozen=True, slots=True)
class OntologyId:
    kind: OntologyKind
    value: str

    def __post_init__(self) -> None:
        if not self.value or self.value != self.value.strip():
            raise ValueError("ontology id must be a non-empty trimmed value")
        if any(part == "" for part in self.value.split(".")):
            raise ValueError("ontology id must not contain empty namespace segments")

    def __str__(self) -> str:
        return f"{self.kind.value}:{self.value}"


@dataclass(frozen=True, slots=True)
class Domain:
    id: OntologyId
    name: str
    description: str

    def __post_init__(self) -> None:
        if self.id.kind is not OntologyKind.DOMAIN:
            raise ValueError("Domain requires a domain ontology id")
        if not self.name.strip() or not self.description.strip():
            raise ValueError("Domain requires name and description")


@dataclass(frozen=True, slots=True)
class CapabilityFamily:
    id: OntologyId
    domain_id: OntologyId
    name: str
    description: str

    def __post_init__(self) -> None:
        if self.id.kind is not OntologyKind.CAPABILITY_FAMILY:
            raise ValueError("CapabilityFamily requires a family ontology id")
        if self.domain_id.kind is not OntologyKind.DOMAIN:
            raise ValueError("CapabilityFamily domain_id must reference a domain")
        if not self.name.strip() or not self.description.strip():
            raise ValueError("CapabilityFamily requires name and description")


@dataclass(frozen=True, slots=True)
class Capability:
    id: OntologyId
    family_id: OntologyId
    name: str
    description: str
    version: str = "1.0"

    def __post_init__(self) -> None:
        if self.id.kind is not OntologyKind.CAPABILITY:
            raise ValueError("Capability requires a capability ontology id")
        if self.family_id.kind is not OntologyKind.CAPABILITY_FAMILY:
            raise ValueError("Capability family_id must reference a capability family")
        if not self.name.strip() or not self.description.strip() or not self.version.strip():
            raise ValueError("Capability requires name, description and version")


@dataclass(frozen=True, slots=True)
class Skill:
    id: OntologyId
    capability_id: OntologyId
    name: str
    description: str

    def __post_init__(self) -> None:
        if self.id.kind is not OntologyKind.SKILL:
            raise ValueError("Skill requires a skill ontology id")
        if self.capability_id.kind is not OntologyKind.CAPABILITY:
            raise ValueError("Skill capability_id must reference a capability")
        if not self.name.strip() or not self.description.strip():
            raise ValueError("Skill requires name and description")


@dataclass(frozen=True, slots=True)
class Role:
    id: OntologyId
    name: str
    description: str

    def __post_init__(self) -> None:
        if self.id.kind is not OntologyKind.ROLE:
            raise ValueError("Role requires a role ontology id")
        if not self.name.strip() or not self.description.strip():
            raise ValueError("Role requires name and description")


@dataclass(frozen=True, slots=True)
class Archetype:
    id: OntologyId
    name: str
    description: str

    def __post_init__(self) -> None:
        if self.id.kind is not OntologyKind.ARCHETYPE:
            raise ValueError("Archetype requires an archetype ontology id")
        if not self.name.strip() or not self.description.strip():
            raise ValueError("Archetype requires name and description")


@dataclass(frozen=True, slots=True)
class OntologyRelation:
    subject: OntologyId
    predicate: str
    object: OntologyId

    def __post_init__(self) -> None:
        if not self.predicate.strip():
            raise ValueError("ontology relation predicate is required")


def implements(agent_id: OntologyId, capability_id: OntologyId) -> OntologyRelation:
    return OntologyRelation(agent_id, "implements", capability_id)


def supports(agent_id: OntologyId, capability_id: OntologyId) -> OntologyRelation:
    return OntologyRelation(agent_id, "supports", capability_id)


def requires(capability_id: OntologyId, required_capability_id: OntologyId) -> OntologyRelation:
    return OntologyRelation(capability_id, "requires_capability", required_capability_id)
