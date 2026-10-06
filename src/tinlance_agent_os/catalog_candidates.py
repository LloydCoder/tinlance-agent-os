"""Governed candidate pipeline for Agent Catalog v3.

Candidate records are untrusted inputs. Canonical taxonomy publication is
explicitly review-gated and never grants execution authority.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from enum import StrEnum


class CandidateState(StrEnum):
    DISCOVERED = "discovered"
    NORMALIZED = "normalized"
    CLUSTERED = "clustered"
    CANDIDATE = "candidate"
    VALIDATED = "validated"
    REVIEWED = "reviewed"
    CANONICAL = "canonical"
    DEPRECATED = "deprecated"


_ALLOWED_TRANSITIONS: dict[CandidateState, frozenset[CandidateState]] = {
    CandidateState.DISCOVERED: frozenset({CandidateState.NORMALIZED}),
    CandidateState.NORMALIZED: frozenset({CandidateState.CLUSTERED}),
    CandidateState.CLUSTERED: frozenset({CandidateState.CANDIDATE}),
    CandidateState.CANDIDATE: frozenset({CandidateState.VALIDATED}),
    CandidateState.VALIDATED: frozenset({CandidateState.REVIEWED}),
    CandidateState.REVIEWED: frozenset({CandidateState.CANONICAL}),
    CandidateState.CANONICAL: frozenset({CandidateState.DEPRECATED}),
    CandidateState.DEPRECATED: frozenset(),
}


@dataclass(frozen=True, slots=True)
class TaxonomyCandidate:
    name: str
    description: str
    domain: str
    capabilities: tuple[str, ...]
    skills: tuple[str, ...] = ()
    source_refs: tuple[str, ...] = ()
    state: CandidateState = CandidateState.DISCOVERED
    canonical_id: str = ""

    def __post_init__(self) -> None:
        if not self.name.strip() or not self.description.strip() or not self.domain.strip():
            raise ValueError("candidate name, description and domain are required")
        if not self.capabilities:
            raise ValueError("candidate requires at least one capability")
        if not self.source_refs:
            raise ValueError("candidate provenance is required")
        if self.state is CandidateState.CANONICAL and not self.canonical_id.strip():
            raise ValueError("canonical candidates require canonical_id")
        if self.state is not CandidateState.CANONICAL and self.canonical_id:
            raise ValueError("canonical_id is only valid for canonical candidates")

    @property
    def semantic_key(self) -> str:
        return "|".join(
            (
                normalize(self.domain),
                normalize(self.name),
                normalize(self.description),
                ",".join(sorted(normalize(value) for value in self.capabilities)),
                ",".join(sorted(normalize(value) for value in self.skills)),
            )
        )

    @property
    def fingerprint(self) -> str:
        return hashlib.sha256(self.semantic_key.encode("utf-8")).hexdigest()

    def transition(self, target: CandidateState, *, canonical_id: str = "") -> TaxonomyCandidate:
        if target not in _ALLOWED_TRANSITIONS[self.state]:
            raise ValueError(f"invalid candidate transition: {self.state} -> {target}")
        if target is CandidateState.CANONICAL and not canonical_id.strip():
            raise ValueError("canonical publication requires canonical_id")
        if target is not CandidateState.CANONICAL and canonical_id:
            raise ValueError("canonical_id is only valid for canonical candidates")
        return TaxonomyCandidate(
            name=self.name,
            description=self.description,
            domain=self.domain,
            capabilities=self.capabilities,
            skills=self.skills,
            source_refs=self.source_refs,
            state=target,
            canonical_id=canonical_id if target is CandidateState.CANONICAL else "",
        )

    def normalized(self) -> TaxonomyCandidate:
        if self.state is not CandidateState.DISCOVERED:
            raise ValueError("only discovered candidates may be normalized")
        return TaxonomyCandidate(
            name=normalize(self.name),
            description=normalize(self.description),
            domain=normalize(self.domain),
            capabilities=tuple(sorted({normalize(value) for value in self.capabilities})),
            skills=tuple(sorted({normalize(value) for value in self.skills})),
            source_refs=tuple(sorted({ref.strip() for ref in self.source_refs if ref.strip()})),
            state=CandidateState.NORMALIZED,
        )


def normalize(value: str) -> str:
    return re.sub(r"\s+", " ", value.strip().lower())


def deduplicate(candidates: tuple[TaxonomyCandidate, ...]) -> tuple[TaxonomyCandidate, ...]:
    """Normalize discovered records and retain one deterministic representative."""
    representatives: dict[str, TaxonomyCandidate] = {}
    for candidate in candidates:
        normalized = candidate.normalized()
        key = normalized.semantic_key
        current = representatives.get(key)
        if current is None or (
            len(normalized.source_refs),
            normalized.fingerprint,
        ) > (
            len(current.source_refs),
            current.fingerprint,
        ):
            representatives[key] = normalized
    return tuple(sorted(representatives.values(), key=lambda item: item.fingerprint))


def cluster_candidate(candidate: TaxonomyCandidate) -> TaxonomyCandidate:
    if candidate.state is not CandidateState.NORMALIZED:
        raise ValueError("only normalized candidates may be clustered")
    return candidate.transition(CandidateState.CLUSTERED)


def mark_candidate(candidate: TaxonomyCandidate) -> TaxonomyCandidate:
    if candidate.state is not CandidateState.CLUSTERED:
        raise ValueError("only clustered candidates may become candidates")
    return candidate.transition(CandidateState.CANDIDATE)


def validate_candidates(candidates: tuple[TaxonomyCandidate, ...]) -> tuple[TaxonomyCandidate, ...]:
    """Advance candidate records to VALIDATED only when structural gates pass."""
    validated: list[TaxonomyCandidate] = []
    for candidate in candidates:
        if candidate.state is not CandidateState.CANDIDATE:
            raise ValueError("only candidate-state records may be validated")
        if len(candidate.name) < 3:
            raise ValueError("candidate name is too short")
        if len(candidate.description) < 20:
            raise ValueError("candidate description is too short")
        if any(not value.strip() for value in candidate.capabilities):
            raise ValueError("candidate capabilities must be non-empty")
        validated.append(candidate.transition(CandidateState.VALIDATED))
    return tuple(validated)


def promote_for_review(candidate: TaxonomyCandidate) -> TaxonomyCandidate:
    """Move a validated candidate to review; never directly to canonical."""
    return candidate.transition(CandidateState.REVIEWED)


def publish_canonical(candidate: TaxonomyCandidate, canonical_id: str) -> TaxonomyCandidate:
    """Publish only an explicitly reviewed candidate under a stable canonical ID."""
    return candidate.transition(CandidateState.CANONICAL, canonical_id=canonical_id)


def deprecate(candidate: TaxonomyCandidate) -> TaxonomyCandidate:
    """Remove a canonical record from the active canonical set."""
    return candidate.transition(CandidateState.DEPRECATED)
