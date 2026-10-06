"""Governed Agent Catalog v3 taxonomy foundation.

The taxonomy is an extensible semantic registry, not an authorization plane.
Canonical archetypes describe a kind of agent; profiles and instances remain
separate layers. Candidate generation is never equivalent to publication.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
import hashlib
import re


_ID_RE = re.compile(r"^[a-z0-9]+(?:[._-][a-z0-9]+)*$")


class TaxonomyStatus(StrEnum):
    DISCOVERED = "discovered"
    NORMALIZED = "normalized"
    CLUSTERED = "clustered"
    CANDIDATE = "candidate"
    VALIDATED = "validated"
    REVIEWED = "reviewed"
    CANONICAL = "canonical"
    DEPRECATED = "deprecated"


@dataclass(frozen=True, slots=True)
class TaxonomyProvenance:
    source_id: str
    source_type: str
    reference: str
    method: str

    def __post_init__(self) -> None:
        if not all(value.strip() for value in (self.source_id, self.source_type, self.reference, self.method)):
            raise ValueError("taxonomy provenance fields are required")


@dataclass(frozen=True, slots=True)
class CanonicalAgentArchetype:
    """A stable semantic kind of agent, independent of implementation."""

    id: str
    version: str
    name: str
    description: str
    domain_id: str
    capability_ids: tuple[str, ...]
    skill_ids: tuple[str, ...]
    inclusion_criteria: tuple[str, ...]
    exclusion_criteria: tuple[str, ...]
    provenance: tuple[TaxonomyProvenance, ...]
    status: TaxonomyStatus = TaxonomyStatus.CANDIDATE
    aliases: tuple[str, ...] = ()
    supersedes: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not _ID_RE.fullmatch(self.id):
            raise ValueError("invalid canonical archetype id")
        if not self.version.strip() or not self.name.strip() or not self.description.strip():
            raise ValueError("id, version, name and description are required")
        if not _ID_RE.fullmatch(self.domain_id):
            raise ValueError("invalid domain id")
        if not self.capability_ids:
            raise ValueError("at least one capability is required")
        if not self.provenance:
            raise ValueError("canonical taxonomy entries require provenance")
        if not self.inclusion_criteria:
            raise ValueError("inclusion criteria are required")
        if self.status is TaxonomyStatus.CANONICAL and not self.exclusion_criteria:
            raise ValueError("canonical entries require exclusion criteria")
        if len(set(self.aliases)) != len(self.aliases):
            raise ValueError("duplicate aliases are not permitted")
        if self.id in self.aliases:
            raise ValueError("canonical id cannot also be an alias")

    @property
    def semantic_key(self) -> str:
        parts = (
            self.domain_id,
            *sorted(self.capability_ids),
            *sorted(self.skill_ids),
            self.name.casefold().strip(),
        )
        return "|".join(parts)

    @property
    def semantic_digest(self) -> str:
        return hashlib.sha256(self.semantic_key.encode("utf-8")).hexdigest()

    def to_record(self) -> dict[str, object]:
        return {
            "schema": "tinlance.agent-archetype.v1",
            "id": self.id,
            "version": self.version,
            "name": self.name,
            "description": self.description,
            "domain": self.domain_id,
            "capabilities": list(self.capability_ids),
            "skills": list(self.skill_ids),
            "inclusion_criteria": list(self.inclusion_criteria),
            "exclusion_criteria": list(self.exclusion_criteria),
            "provenance": [
                {
                    "source_id": item.source_id,
                    "source_type": item.source_type,
                    "reference": item.reference,
                    "method": item.method,
                }
                for item in self.provenance
            ],
            "status": self.status.value,
            "aliases": list(self.aliases),
            "supersedes": list(self.supersedes),
            "semantic_digest": self.semantic_digest,
        }


@dataclass(frozen=True, slots=True)
class TaxonomyAlias:
    alias: str
    canonical_id: str
    reason: str

    def __post_init__(self) -> None:
        if not self.alias.strip() or not self.canonical_id.strip() or not self.reason.strip():
            raise ValueError("taxonomy alias fields are required")


@dataclass(frozen=True, slots=True)
class TaxonomyCompatibility:
    seed_id: str
    canonical_id: str
    relation: str

    def __post_init__(self) -> None:
        if not all(value.strip() for value in (self.seed_id, self.canonical_id, self.relation)):
            raise ValueError("taxonomy compatibility fields are required")
        if self.relation not in {"equivalent", "specialized", "generalized", "superseded"}:
            raise ValueError("unsupported taxonomy compatibility relation")
