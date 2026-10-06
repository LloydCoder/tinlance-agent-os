"""Governed candidate pipeline for Agent Catalog v3.

Candidate records are untrusted inputs. Canonical taxonomy publication is
explicitly outside this module and remains review-gated.
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
        if not self.capabilities or any(not value.strip() for value in self.capabilities):
            raise ValueError("candidate capabilities must be non-empty")
        if any(not value.strip() for value in self.skills):
            raise ValueError("candidate skills must be non-empty")
        if not self.source_refs or any(not ref.strip() for ref in self.source_refs):
            raise ValueError("candidate provenance must contain non-empty references")
        if self.state is CandidateState.CANONICAL and not self.canonical_id.strip():
            raise ValueError("canonical candidates require canonical_id")

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

    def normalized(self) -> TaxonomyCandidate:
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
    text = re.sub(r"\s+", " ", value.strip().lower())
    return text


def deduplicate(candidates: tuple[TaxonomyCandidate, ...]) -> tuple[TaxonomyCandidate, ...]:
    """Normalize and retain one deterministic representative per semantic key."""
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


def validate_candidates(
    candidates: tuple[TaxonomyCandidate, ...],
) -> tuple[TaxonomyCandidate, ...]:
    """Advance normalized candidates to VALIDATED only when structural gates pass."""
    validated: list[TaxonomyCandidate] = []
    for candidate in candidates:
        normalized = candidate.normalized()
        if len(normalized.name) < 3:
            raise ValueError("candidate name is too short")
        if len(normalized.description) < 20:
            raise ValueError("candidate description is too short")
        validated.append(
            TaxonomyCandidate(
                name=normalized.name,
                description=normalized.description,
                domain=normalized.domain,
                capabilities=normalized.capabilities,
                skills=normalized.skills,
                source_refs=normalized.source_refs,
                state=CandidateState.VALIDATED,
            )
        )
    return tuple(validated)


def promote_for_review(candidate: TaxonomyCandidate) -> TaxonomyCandidate:
    """Move a validated candidate to review; never directly to canonical."""
    if candidate.state is not CandidateState.VALIDATED:
        raise ValueError("only validated candidates may enter review")
    return TaxonomyCandidate(
        name=candidate.name,
        description=candidate.description,
        domain=candidate.domain,
        capabilities=candidate.capabilities,
        skills=candidate.skills,
        source_refs=candidate.source_refs,
        state=CandidateState.REVIEWED,
        canonical_id=candidate.canonical_id,
    )
