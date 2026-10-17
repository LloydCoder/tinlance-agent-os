"""Strict 20K canonical expansion gate for Agent Catalog v3."""

from __future__ import annotations

import hashlib
import json
import math
import re
from collections.abc import Iterable
from dataclasses import dataclass

from .catalog_candidates import CandidateState, TaxonomyCandidate
from .catalog_semantics import canonical_semantic_key, normalize_semantic_token

TARGET_COUNT = 20_000
MIN_DOMAINS = 50
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


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

    def __post_init__(self) -> None:
        if not self.release or self.release != self.release.strip():
            raise ValueError("release identifier must be non-empty and normalized")
        for name, value in (
            ("target_count", self.target_count),
            ("canonical_count", self.canonical_count),
            ("domain_count", self.domain_count),
        ):
            if isinstance(value, bool) or not isinstance(value, int):
                raise ValueError(f"{name} must be an integer")
        if self.target_count != TARGET_COUNT:
            raise ValueError("target_count must match the canonical 20K milestone")
        if self.canonical_count < self.target_count:
            raise ValueError("canonical_count must meet the 20K release target")
        if self.domain_count < MIN_DOMAINS:
            raise ValueError("domain_count must meet the minimum domain diversity")
        for name, value in (
            ("provenance_coverage", self.provenance_coverage),
            ("review_coverage", self.review_coverage),
            ("semantic_uniqueness", self.semantic_uniqueness),
        ):
            if (
                isinstance(value, bool)
                or not isinstance(value, (int, float))
                or not math.isfinite(value)
            ):
                raise ValueError(f"{name} must be a finite numeric coverage value")
            if value != 1.0:
                raise ValueError(f"{name} must be 1.0 for a release-qualified inventory")
        if not _SHA256_RE.fullmatch(self.inventory_digest):
            raise ValueError("inventory_digest must be lowercase SHA-256 hex")


def _semantic_key(candidate: TaxonomyCandidate) -> str:
    return canonical_semantic_key(
        candidate.domain,
        candidate.capabilities,
        candidate.skills,
    )


def _inventory_digest(candidates: Iterable[TaxonomyCandidate]) -> str:
    """Digest all release-relevant content, not only matching dimensions."""
    payload = [
        {
            "canonical_id": candidate.canonical_id.strip(),
            "name": candidate.name,
            "description": candidate.description,
            "semantic_key": _semantic_key(candidate),
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


def build_20k_expansion_manifest(
    candidates: Iterable[TaxonomyCandidate],
    *,
    release: str = "catalog-v3-20k",
) -> ExpansionManifest:
    """Prove that an explicit 20K canonical inventory is release-qualified."""
    inventory = tuple(candidates)
    if len(inventory) < TARGET_COUNT:
        raise ValueError(f"20K expansion requires at least {TARGET_COUNT} canonical entries")
    if not release or release != release.strip():
        raise ValueError("release identifier must be non-empty and normalized")
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

    domains = {normalize_semantic_token(candidate.domain) for candidate in inventory}
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
