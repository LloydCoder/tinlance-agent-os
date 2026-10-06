"""GA governance primitives for continuous Agent Catalog v3 evolution."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass

from .catalog_candidates import CandidateState, TaxonomyCandidate


@dataclass(frozen=True, slots=True)
class EvolutionRelease:
    release_id: str
    base_digest: str
    inventory_digest: str
    added_ids: tuple[str, ...]
    deprecated_ids: tuple[str, ...]
    governance_ref: str

    def __post_init__(self) -> None:
        if not self.release_id.strip():
            raise ValueError("release_id is required")
        if not self.base_digest.strip() or not self.inventory_digest.strip():
            raise ValueError("release digests are required")
        if not self.governance_ref.strip():
            raise ValueError("continuous evolution requires governance evidence")
        if set(self.added_ids) & set(self.deprecated_ids):
            raise ValueError("an identifier cannot be added and deprecated in one release")
        if tuple(sorted(set(self.added_ids))) != self.added_ids:
            raise ValueError("added identifiers must be unique and sorted")
        if tuple(sorted(set(self.deprecated_ids))) != self.deprecated_ids:
            raise ValueError("deprecated identifiers must be unique and sorted")


def _digest(candidates: tuple[TaxonomyCandidate, ...]) -> str:
    payload = sorted(
        (
            candidate.canonical_id.strip(),
            candidate.domain.strip().lower(),
            tuple(sorted(value.strip().lower() for value in candidate.capabilities)),
            tuple(sorted(value.strip().lower() for value in candidate.skills)),
            tuple(sorted(candidate.source_refs)),
            candidate.review_ref.strip(),
            candidate.state.value,
        )
        for candidate in candidates
    )
    encoded = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def prepare_evolution_release(
    *,
    base: tuple[TaxonomyCandidate, ...],
    proposed: tuple[TaxonomyCandidate, ...],
    release_id: str,
    governance_ref: str,
) -> EvolutionRelease:
    """Prepare a descriptive release manifest; publication remains external."""
    base_ids = {candidate.canonical_id.strip() for candidate in base}
    proposed_ids = {candidate.canonical_id.strip() for candidate in proposed}

    if any(
        candidate.state not in {CandidateState.CANONICAL, CandidateState.DEPRECATED}
        for candidate in proposed
    ):
        raise ValueError("evolution inventories may contain only canonical or deprecated records")
    if any(not candidate.review_ref.strip() for candidate in proposed):
        raise ValueError("every evolved record requires review evidence")

    added = tuple(sorted(proposed_ids - base_ids))
    deprecated = tuple(
        sorted(
            candidate.canonical_id.strip()
            for candidate in proposed
            if candidate.state is CandidateState.DEPRECATED
        )
    )
    return EvolutionRelease(
        release_id=release_id,
        base_digest=_digest(base),
        inventory_digest=_digest(proposed),
        added_ids=added,
        deprecated_ids=deprecated,
        governance_ref=governance_ref,
    )
