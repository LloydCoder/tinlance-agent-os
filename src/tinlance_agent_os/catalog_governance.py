"""GA governance primitives for continuous Agent Catalog v3 evolution."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass

from .catalog_candidates import CandidateState, TaxonomyCandidate
from .catalog_semantics import canonical_semantic_key

_CANONICAL_ID_RE = re.compile(r"^[a-z0-9]+(?:[._-][a-z0-9]+)*$")
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


@dataclass(frozen=True, slots=True)
class EvolutionRelease:
    release_id: str
    base_digest: str
    inventory_digest: str
    added_ids: tuple[str, ...]
    deprecated_ids: tuple[str, ...]
    governance_ref: str

    def __post_init__(self) -> None:
        if not self.release_id or self.release_id != self.release_id.strip():
            raise ValueError("release_id must be non-empty and normalized")
        if not _SHA256_RE.fullmatch(self.base_digest):
            raise ValueError("base_digest must be lowercase SHA-256 hex")
        if not _SHA256_RE.fullmatch(self.inventory_digest):
            raise ValueError("inventory_digest must be lowercase SHA-256 hex")
        if not self.governance_ref or self.governance_ref != self.governance_ref.strip():
            raise ValueError("continuous evolution requires normalized governance evidence")
        if set(self.added_ids) & set(self.deprecated_ids):
            raise ValueError("an identifier cannot be added and deprecated in one release")
        if tuple(sorted(set(self.added_ids))) != self.added_ids:
            raise ValueError("added identifiers must be unique and sorted")
        if tuple(sorted(set(self.deprecated_ids))) != self.deprecated_ids:
            raise ValueError("deprecated identifiers must be unique and sorted")
        if any(not _CANONICAL_ID_RE.fullmatch(value) for value in self.added_ids):
            raise ValueError("added identifiers must be valid canonical IDs")
        if any(not _CANONICAL_ID_RE.fullmatch(value) for value in self.deprecated_ids):
            raise ValueError("deprecated identifiers must be valid canonical IDs")


def _validate_inventory(
    candidates: tuple[TaxonomyCandidate, ...],
    *,
    label: str,
) -> None:
    ids = [candidate.canonical_id.strip() for candidate in candidates]
    if any(not _CANONICAL_ID_RE.fullmatch(value) for value in ids):
        raise ValueError(f"{label} inventory contains an invalid canonical ID")
    if len(set(ids)) != len(ids):
        raise ValueError(f"{label} inventory contains duplicate canonical IDs")
    if any(
        candidate.state not in {CandidateState.CANONICAL, CandidateState.DEPRECATED}
        for candidate in candidates
    ):
        raise ValueError(f"{label} inventory may contain only canonical or deprecated records")
    if any(
        not candidate.source_refs or any(not ref.strip() for ref in candidate.source_refs)
        for candidate in candidates
    ):
        raise ValueError(f"{label} inventory requires provenance for every record")
    if any(not candidate.review_ref.strip() for candidate in candidates):
        raise ValueError(f"{label} inventory requires review evidence for every record")
    active_keys = [
        canonical_semantic_key(candidate.domain, candidate.capabilities, candidate.skills)
        for candidate in candidates
        if candidate.state is CandidateState.CANONICAL
    ]
    if len(set(active_keys)) != len(active_keys):
        raise ValueError(f"{label} inventory contains semantic duplicates among canonical records")


def _digest(candidates: tuple[TaxonomyCandidate, ...]) -> str:
    payload = [
        {
            "canonical_id": candidate.canonical_id.strip(),
            "name": candidate.name,
            "description": candidate.description,
            "semantic_key": canonical_semantic_key(
                candidate.domain,
                candidate.capabilities,
                candidate.skills,
            ),
            "source_refs": sorted({ref.strip() for ref in candidate.source_refs}),
            "review_ref": candidate.review_ref.strip(),
            "state": candidate.state.value,
        }
        for candidate in candidates
    ]
    encoded = json.dumps(
        sorted(payload, key=lambda item: item["canonical_id"]),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def prepare_evolution_release(
    *,
    base: tuple[TaxonomyCandidate, ...],
    proposed: tuple[TaxonomyCandidate, ...],
    release_id: str,
    governance_ref: str,
) -> EvolutionRelease:
    """Prepare a descriptive release manifest; publication remains external."""
    _validate_inventory(base, label="base")
    _validate_inventory(proposed, label="proposed")

    base_state_by_id = {candidate.canonical_id.strip(): candidate.state for candidate in base}
    base_ids = set(base_state_by_id)
    proposed_state_by_id = {
        candidate.canonical_id.strip(): candidate.state for candidate in proposed
    }
    proposed_ids = set(proposed_state_by_id)
    missing_ids = base_ids - proposed_ids
    if missing_ids:
        raise ValueError(
            "evolution release cannot delete historical IDs; deprecate them explicitly: "
            + ", ".join(sorted(missing_ids))
        )
    reactivated_ids = {
        canonical_id
        for canonical_id, base_state in base_state_by_id.items()
        if base_state is CandidateState.DEPRECATED
        and proposed_state_by_id[canonical_id] is not CandidateState.DEPRECATED
    }
    if reactivated_ids:
        raise ValueError(
            "deprecated canonical IDs cannot be reactivated: "
            + ", ".join(sorted(reactivated_ids))
        )

    if any(
        candidate.state is CandidateState.DEPRECATED
        and candidate.canonical_id.strip() not in base_ids
        for candidate in proposed
    ):
        raise ValueError("a new taxonomy entry must be canonical before it can be deprecated")

    added = tuple(
        sorted(
            candidate.canonical_id.strip()
            for candidate in proposed
            if candidate.canonical_id.strip() not in base_ids
            and candidate.state is CandidateState.CANONICAL
        )
    )
    deprecated = tuple(
        sorted(
            candidate.canonical_id.strip()
            for candidate in proposed
            if candidate.state is CandidateState.DEPRECATED
            and base_state_by_id.get(candidate.canonical_id.strip()) is CandidateState.CANONICAL
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
