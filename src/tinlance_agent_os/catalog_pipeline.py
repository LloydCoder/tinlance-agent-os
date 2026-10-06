"""Controlled candidate lifecycle for Agent Catalog v3."""
from __future__ import annotations

from dataclasses import dataclass, replace

from .catalog_taxonomy import CanonicalAgentArchetype, TaxonomyStatus

_ALLOWED_TRANSITIONS: dict[TaxonomyStatus, frozenset[TaxonomyStatus]] = {
    TaxonomyStatus.DISCOVERED: frozenset({TaxonomyStatus.NORMALIZED}),
    TaxonomyStatus.NORMALIZED: frozenset({TaxonomyStatus.CLUSTERED}),
    TaxonomyStatus.CLUSTERED: frozenset({TaxonomyStatus.CANDIDATE}),
    TaxonomyStatus.CANDIDATE: frozenset({TaxonomyStatus.VALIDATED}),
    TaxonomyStatus.VALIDATED: frozenset({TaxonomyStatus.REVIEWED}),
    TaxonomyStatus.REVIEWED: frozenset({TaxonomyStatus.CANONICAL}),
    TaxonomyStatus.CANONICAL: frozenset({TaxonomyStatus.DEPRECATED}),
    TaxonomyStatus.DEPRECATED: frozenset(),
}

@dataclass(frozen=True, slots=True)
class TaxonomyTransition:
    archetype_id: str
    from_status: TaxonomyStatus
    to_status: TaxonomyStatus
    reason: str

    def __post_init__(self) -> None:
        if not self.archetype_id.strip() or not self.reason.strip():
            raise ValueError("transition identity and reason are required")
        if self.to_status not in _ALLOWED_TRANSITIONS[self.from_status]:
            raise ValueError("invalid taxonomy lifecycle transition")

class CandidatePipeline:
    """Apply governed lifecycle transitions; never grant runtime authority."""

    @staticmethod
    def transition(archetype: CanonicalAgentArchetype, to_status: TaxonomyStatus, reason: str) -> tuple[CanonicalAgentArchetype, TaxonomyTransition]:
        event = TaxonomyTransition(archetype.id, archetype.status, to_status, reason)
        return replace(archetype, status=to_status), event
