"""Strict release gates for Agent Catalog v3 canonical inventory.

This module does not create taxonomy entries. It only proves that an existing,
reviewed canonical inventory satisfies the 10K release contract.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
from collections.abc import Iterable
from dataclasses import dataclass

from .catalog_candidates import CandidateState, TaxonomyCandidate
from .catalog_semantics import canonical_semantic_key, normalize_semantic_token


@dataclass(frozen=True, slots=True)
class CatalogReleaseManifest:
    release: str
    target_count: int
    canonical_count: int
    domain_count: int
    provenance_coverage: float
    semantic_uniqueness: float
    inventory_digest: str

    def __post_init__(self) -> None:
        if not self.release or self.release != self.release.strip():
            raise ValueError("release identifier must be non-empty and normalized")
        for count_name, count_value in (
            ("target_count", self.target_count),
            ("canonical_count", self.canonical_count),
            ("domain_count", self.domain_count),
        ):
            if isinstance(count_value, bool) or not isinstance(count_value, int):
                raise ValueError(f"{count_name} must be an integer")
        if self.target_count != 10_000:
            raise ValueError("target_count must match the canonical 10K milestone")
        if self.canonical_count < self.target_count:
            raise ValueError("canonical_count must meet the 10K release target")
        if self.domain_count < 30:
            raise ValueError("domain_count must meet the minimum domain diversity")
        for coverage_name, coverage_value in (
            ("provenance_coverage", self.provenance_coverage),
            ("semantic_uniqueness", self.semantic_uniqueness),
        ):
            if (
                isinstance(coverage_value, bool)
                or not isinstance(coverage_value, (int, float))
                or not math.isfinite(coverage_value)
            ):
                raise ValueError(f"{coverage_name} must be a finite numeric coverage value")
            if coverage_value != 1.0:
                raise ValueError(f"{coverage_name} must be 1.0 for a qualified release")
        if not re.fullmatch(r"[0-9a-f]{64}", self.inventory_digest):
            raise ValueError("inventory_digest must be lowercase SHA-256 hex")


def _semantic_archetype_key(candidate: TaxonomyCandidate) -> str:
    """Identity for an archetype, independent of display name/description."""
    return canonical_semantic_key(
        candidate.domain,
        candidate.capabilities,
        candidate.skills,
    )


def _inventory_digest(candidates: Iterable[TaxonomyCandidate]) -> str:
    """Digest the complete release-relevant inventory, independent of input order."""
    payload = [
        {
            "canonical_id": candidate.canonical_id.strip(),
            "name": candidate.name,
            "description": candidate.description,
            "semantic_key": _semantic_archetype_key(candidate),
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
    if min_domains != 30:
        raise ValueError("Phase 30 release diversity threshold is fixed at 30 domains")
    if len(inventory) < target_count:
        raise ValueError(f"10K release requires at least {target_count} canonical entries")

    canonical_ids = [candidate.canonical_id.strip() for candidate in inventory]
    if any(candidate.state is not CandidateState.CANONICAL for candidate in inventory):
        raise ValueError("10K release requires every entry to be canonical")
    if any(not candidate_id for candidate_id in canonical_ids):
        raise ValueError("10K release requires stable canonical identifiers")
    if len(set(canonical_ids)) != len(canonical_ids):
        raise ValueError("10K release requires unique canonical identifiers")

    semantic_keys = [_semantic_archetype_key(candidate) for candidate in inventory]
    if len(set(semantic_keys)) != len(semantic_keys):
        raise ValueError("10K release requires semantic uniqueness")

    provenance_count = sum(bool(candidate.source_refs) for candidate in inventory)
    provenance_coverage = provenance_count / len(inventory)
    if provenance_coverage != 1.0:
        raise ValueError("10K release requires 100% provenance coverage")
    if any(not candidate.review_ref.strip() for candidate in inventory):
        raise ValueError("10K release requires review evidence for every entry")

    domains = {normalize_semantic_token(candidate.domain) for candidate in inventory}
    if len(domains) < min_domains:
        raise ValueError(f"10K release requires at least {min_domains} distinct domains")

    if not release.strip():
        raise ValueError("release identifier is required")
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
