"""Deterministic Agent Catalog v2 GA readiness contract."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class GaCheck:
    name: str
    passed: bool
    evidence_ref: str


@dataclass(frozen=True, slots=True)
class CatalogGaReadiness:
    release: str
    ontology_version: str
    profile_schema_version: str
    seed_entries: int
    unresolved_taxonomy_entries: int
    checks: tuple[GaCheck, ...]

    @property
    def ready(self) -> bool:
        required = {
            "ci",
            "architecture",
            "security",
            "evaluation",
            "supply_chain",
            "documentation",
        }
        observed = {check.name for check in self.checks}
        return (
            self.seed_entries == 420
            and self.unresolved_taxonomy_entries == 0
            and required.issubset(observed)
            and all(check.passed for check in self.checks if check.name in required)
            and all(check.evidence_ref.strip() for check in self.checks)
        )
