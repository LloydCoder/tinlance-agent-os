"""Strict release gates for Agent Catalog v3 canonical inventory.

This module does not create taxonomy entries. It only proves that an existing,
reviewed canonical inventory satisfies the 10K release contract.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Iterable

from .catalog_candidates import CandidateState, TaxonomyCandidate


@dataclass(frozen=True, slots=True)
class CatalogReleaseManifest:
    release: str
    target_count: int
    canonical_count: int
    domain_count: int
    provenance_coverage: float
    semantic_uniqueness: float
    inventory_digest: str


def _canonical_key(candidate: TaxonomyCandidate) -> str:
    return "|".join(
        (
            candidate.canonical_id.strip(),
            candidate.fingerprint,
            ",".join(sorted(ref.strip() for ref in candidate.source_refs)),
        )
    )


def _inventory_digest(candidates: Iterable[TaxonomyCandidate]) -> str:
    payload = [_canonical_key(candidate) for candidate in candidates]
    return hashlib.sha256(
        json.dumps(sorted(payload), separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def build_10k_release_manifest(
    candidates: Iterable[TaxonomyCandidate],
    *,
    release: str = "catalog-v3-10k",
    target_count: int = 10_000,
    min_domains: int = 30,
) -> CatalogReleaseManifest:
    """Fail closed unless the supplied canonical inventory meets the 10K contract."""
    inventory = tuple(candidates)
    if target_count != 10_000:
        raise ValueError("Phase 30 release target is fixed at 10,000 canonical entries")
    if len(inventory) < target_count:
        raise ValueError(f"10K release requires at least {target_count} canonical entries")

    canonical_ids = [candidate.canonical_id.strip() for candidate in inventory]
    if any(candidate.state is not CandidateState.CANONICAL for candidate in inventory):
        raise ValueError("10K release requires every entry to be canonical")
    if any(not candidate_id for candidate_id in canonical_ids):
        raise ValueError("10K release requires stable canonical identifiers")
    if len(set(canonical_ids)) != len(canonical_ids):
        raise ValueError("10K release requires unique canonical identifiers")

    semantic_keys = [candidate.semantic_key for candidate in inventory]
    if len(set(semantic_keys)) != len(semantic_keys):
        raise ValueError("10K release requires semantic uniqueness")

    provenance_coverage = sum(bool(candidate.source_refs) for candidate in inventory) / len(inventory)
    if provenance_coverage != 1.0:
        raise ValueError("10K release requires 100% provenance coverage")

    domains = {candidate.domain.strip().lower() for candidate in inventory}
    if len(domains) < min_domains:
        raise ValueError(f"10K release requires at least {min_domains} distinct domains")

    digest = _inventory_digest(inventory)
    return CatalogReleaseManifest(
        release=release,
        target_count=target_count,
        canonical_count=len(inventory),
        domain_count=len(domains),
        provenance_coverage=provenance_coverage,
        semantic_uniqueness=1.0,
        inventory_digest=digest,
    )
