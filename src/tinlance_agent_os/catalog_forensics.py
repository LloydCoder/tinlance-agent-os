"""Forensic validation of the Agent Catalog v3 canonical boundary."""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Iterable
from dataclasses import dataclass

from .catalog_candidates import CandidateState, TaxonomyCandidate

_CANONICAL_ID_RE = re.compile(r"^[a-z0-9]+(?:[._-][a-z0-9]+)*$")


@dataclass(frozen=True, slots=True)
class ForensicAuditReport:
    inspected_count: int
    canonical_count: int
    domain_count: int
    provenance_coverage: float
    review_coverage: float
    semantic_uniqueness: float
    failures: tuple[str, ...]
    audit_digest: str

    @property
    def passed(self) -> bool:
        return not self.failures


def _semantic_key(candidate: TaxonomyCandidate) -> str:
    return "|".join(
        (
            candidate.domain.strip().lower(),
            ",".join(sorted(value.strip().lower() for value in candidate.capabilities)),
            ",".join(sorted(value.strip().lower() for value in candidate.skills)),
        )
    )


def _digest(
    candidates: Iterable[TaxonomyCandidate], failures: tuple[str, ...]
) -> str:
    payload = {
        "entries": sorted(
            (
                candidate.canonical_id.strip(),
                _semantic_key(candidate),
                tuple(sorted(candidate.source_refs)),
                candidate.review_ref.strip(),
            )
            for candidate in candidates
        ),
        "failures": failures,
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def audit_canonical_inventory(
    candidates: Iterable[TaxonomyCandidate],
    *,
    minimum_count: int = 20_000,
    minimum_domains: int = 50,
) -> ForensicAuditReport:
    """Run cross-phase deterministic checks and fail closed on policy violations."""
    inventory = tuple(candidates)
    failures: list[str] = []

    if minimum_count <= 0 or minimum_domains <= 0:
        raise ValueError("forensic thresholds must be positive")
    if len(inventory) < minimum_count:
        failures.append(f"canonical count below required minimum {minimum_count}")

    canonical_count = sum(
        candidate.state is CandidateState.CANONICAL for candidate in inventory
    )
    if canonical_count != len(inventory):
        failures.append("inventory contains non-canonical lifecycle records")

    canonical_ids = [candidate.canonical_id.strip() for candidate in inventory]
    if any(not _CANONICAL_ID_RE.fullmatch(value) for value in canonical_ids):
        failures.append("inventory contains invalid canonical identifiers")
    if len(set(canonical_ids)) != len(canonical_ids):
        failures.append("inventory contains duplicate canonical identifiers")

    semantic_keys = [_semantic_key(candidate) for candidate in inventory]
    if len(set(semantic_keys)) != len(semantic_keys):
        failures.append("inventory contains semantic archetype duplicates")

    provenance_count = sum(bool(candidate.source_refs) for candidate in inventory)
    review_count = sum(bool(candidate.review_ref.strip()) for candidate in inventory)
    provenance_coverage = provenance_count / len(inventory) if inventory else 0.0
    review_coverage = review_count / len(inventory) if inventory else 0.0
    if provenance_coverage != 1.0:
        failures.append("provenance coverage is below 100 percent")
    if review_coverage != 1.0:
        failures.append("review evidence coverage is below 100 percent")

    domains = {candidate.domain.strip().lower() for candidate in inventory}
    if len(domains) < minimum_domains:
        failures.append(f"domain diversity below required minimum {minimum_domains}")

    failure_tuple = tuple(sorted(set(failures)))
    return ForensicAuditReport(
        inspected_count=len(inventory),
        canonical_count=canonical_count,
        domain_count=len(domains),
        provenance_coverage=provenance_coverage,
        review_coverage=review_coverage,
        semantic_uniqueness=(
            1.0 if inventory and len(set(semantic_keys)) == len(semantic_keys) else 0.0
        ),
        failures=failure_tuple,
        audit_digest=_digest(inventory, failure_tuple),
    )
