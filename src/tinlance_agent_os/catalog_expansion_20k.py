"""Strict 20K canonical expansion gate for Agent Catalog v3."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable
from dataclasses import dataclass

from .catalog_candidates import CandidateState, TaxonomyCandidate

TARGET_COUNT = 20_000
MIN_DOMAINS = 50


@dataclass(frozen=True, slots=True)
class ExpansionManifest:
    release: str
    target_count: int
    canonical_count: int
    domain_count: int
    provenance_coverage: float
    review_coverage: float
    semantic_uniqueness: float
    inventory_digest: str


def _semantic_key(candidate: TaxonomyCandidate) -> str:
    return "|".join(
        (
            candidate.domain.strip().lower(),
            ",".join(sorted(value.strip().lower() for value in candidate.capabilities)),
            ",".join(sorted(value.strip().lower() for value in candidate.skills)),
        )
    )


def _inventory_digest(candidates: Iterable[TaxonomyCandidate]) -> str:
    payload = [
        "|".join(
            (
                candidate.canonical_id.strip(),
                _semantic_key(candidate),
                ",".join(sorted(ref.strip() for ref in candidate.source_refs)),
                candidate.review_ref.strip(),
            )
        )
        for candidate in candidates
    ]
    encoded = json.dumps(sorted(payload), separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def build_20k_expansion_manifest(
    candidates: Iterable[TaxonomyCandidate],
    *,
    release: str = "catalog-v3-20k",
) -> ExpansionManifest:
    """Prove that an explicit 20K canonical inventory is release-qualified."""
    inventory = tuple(candidates)
    if len(inventory) < TARGET_COUNT:
        raise ValueError(f"20K expansion requires at least {TARGET_COUNT} canonical entries")
    if not release.strip():
        raise ValueError("release identifier is required")
    if any(candidate.state is not CandidateState.CANONICAL for candidate in inventory):
        raise ValueError("20K expansion requires every entry to be canonical")
    if any(not candidate.canonical_id.strip() for candidate in inventory):
        raise ValueError("20K expansion requires stable canonical identifiers")
    if any(not candidate.source_refs for candidate in inventory):
        raise ValueError("20K expansion requires provenance for every entry")
    if any(not candidate.review_ref.strip() for candidate in inventory):
        raise ValueError("20K expansion requires review evidence for every entry")

    canonical_ids = [candidate.canonical_id.strip() for candidate in inventory]
    if len(set(canonical_ids)) != len(canonical_ids):
        raise ValueError("20K expansion requires unique canonical identifiers")

    semantic_keys = [_semantic_key(candidate) for candidate in inventory]
    if len(set(semantic_keys)) != len(semantic_keys):
        raise ValueError("20K expansion requires semantic uniqueness")

    domains = {candidate.domain.strip().lower() for candidate in inventory}
    if len(domains) < MIN_DOMAINS:
        raise ValueError(f"20K expansion requires at least {MIN_DOMAINS} distinct domains")

    return ExpansionManifest(
        release=release,
        target_count=TARGET_COUNT,
        canonical_count=len(inventory),
        domain_count=len(domains),
        provenance_coverage=1.0,
        review_coverage=1.0,
        semantic_uniqueness=1.0,
        inventory_digest=_inventory_digest(inventory),
    )
