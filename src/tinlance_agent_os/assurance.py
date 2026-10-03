"""Enterprise GA readiness and assurance contracts.

M41 records release compatibility, assurance checks, evidence references and
operational readiness. It does not claim that an external certification has
been obtained; external auditors, penetration tests, SOC 2/ISO assessments and
customer-specific attestations remain outside the repository.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from typing import Final, Literal, cast

from .store import StateStore

CheckState = Literal["pending", "passed", "failed", "waived"]
EvidenceKind = Literal["ci", "security", "performance", "chaos", "dr", "compliance", "supply_chain"]


_SCHEMA: Final = """
CREATE TABLE IF NOT EXISTS ga_releases (
    release_id TEXT PRIMARY KEY,
    version TEXT NOT NULL,
    api_major INTEGER NOT NULL CHECK(api_major >= 0),
    schema_version TEXT NOT NULL,
    artifact_digest TEXT NOT NULL,
    sbom_ref TEXT NOT NULL,
    provenance_ref TEXT NOT NULL,
    generation INTEGER NOT NULL CHECK(generation >= 0)
);

CREATE TABLE IF NOT EXISTS ga_checks (
    check_id TEXT PRIMARY KEY,
    release_id TEXT NOT NULL,
    kind TEXT NOT NULL CHECK(
        kind IN ('ci','security','performance','chaos','dr','compliance','supply_chain')
    ),
    name TEXT NOT NULL,
    state TEXT NOT NULL CHECK(state IN ('pending','passed','failed','waived')),
    evidence_ref TEXT,
    generation INTEGER NOT NULL CHECK(generation >= 0)
);

CREATE TABLE IF NOT EXISTS ga_compatibility (
    compatibility_id TEXT PRIMARY KEY,
    release_id TEXT NOT NULL,
    component TEXT NOT NULL,
    minimum_version TEXT NOT NULL,
    maximum_version TEXT,
    status TEXT NOT NULL CHECK(status IN ('supported','deprecated','blocked')),
    generation INTEGER NOT NULL CHECK(generation >= 0)
);
"""


@dataclass(frozen=True, slots=True)
class GARelease:
    release_id: str
    version: str
    api_major: int
    schema_version: str
    artifact_digest: str
    sbom_ref: str
    provenance_ref: str
    generation: int = 0


@dataclass(frozen=True, slots=True)
class GACheck:
    check_id: str
    release_id: str
    kind: EvidenceKind
    name: str
    state: CheckState
    evidence_ref: str | None = None
    generation: int = 0


@dataclass(frozen=True, slots=True)
class GACompatibility:
    compatibility_id: str
    release_id: str
    component: str
    minimum_version: str
    maximum_version: str | None
    status: Literal["supported", "deprecated", "blocked"]
    generation: int = 0


@dataclass(frozen=True, slots=True)
class GAReadiness:
    release_id: str
    ready: bool
    checks_total: int
    checks_passed: int
    checks_failed: int
    checks_pending: int
    checks_waived: int


class EnterpriseGARuntime:
    """Durable evidence ledger for enterprise release readiness."""

    def __init__(self, store: StateStore) -> None:
        self.store = store
        with sqlite3.connect(store.path) as db:
            db.executescript(_SCHEMA)

    @staticmethod
    def _required(value: str, label: str) -> None:
        if not value.strip():
            raise ValueError(f"{label} is required")

    def register_release(self, release: GARelease) -> GARelease:
        self._required(release.release_id, "release_id")
        self._required(release.version, "version")
        self._required(release.schema_version, "schema_version")
        self._required(release.artifact_digest, "artifact_digest")
        self._required(release.sbom_ref, "sbom_ref")
        self._required(release.provenance_ref, "provenance_ref")
        if release.api_major < 0:
            raise ValueError("api_major must be non-negative")
        with sqlite3.connect(self.store.path) as db:
            db.execute(
                """INSERT INTO ga_releases
                (release_id,version,api_major,schema_version,artifact_digest,sbom_ref,
                 provenance_ref,generation)
                VALUES (?,?,?,?,?,?,?,?)""",
                (
                    release.release_id,
                    release.version,
                    release.api_major,
                    release.schema_version,
                    release.artifact_digest,
                    release.sbom_ref,
                    release.provenance_ref,
                    release.generation,
                ),
            )
        return release

    def record_check(self, check: GACheck) -> GACheck:
        self._required(check.check_id, "check_id")
        self._required(check.release_id, "release_id")
        self._required(check.name, "name")
        if check.state in {"passed", "failed"} and not check.evidence_ref:
            raise ValueError("completed assurance checks require evidence_ref")
        with sqlite3.connect(self.store.path) as db:
            release = db.execute(
                "SELECT 1 FROM ga_releases WHERE release_id=?", (check.release_id,)
            ).fetchone()
            if release is None:
                raise KeyError(f"unknown release: {check.release_id}")
            db.execute(
                """INSERT INTO ga_checks
                (check_id,release_id,kind,name,state,evidence_ref,generation)
                VALUES (?,?,?,?,?,?,?)""",
                (
                    check.check_id,
                    check.release_id,
                    check.kind,
                    check.name,
                    check.state,
                    check.evidence_ref,
                    check.generation,
                ),
            )
        return check

    def transition_check(
        self,
        check_id: str,
        *,
        state: CheckState,
        evidence_ref: str | None,
        expected_generation: int,
    ) -> GACheck:
        self._required(check_id, "check_id")
        if state in {"passed", "failed"} and not evidence_ref:
            raise ValueError("completed assurance checks require evidence_ref")
        with sqlite3.connect(self.store.path) as db:
            row = db.execute(
                """SELECT check_id,release_id,kind,name,state,evidence_ref,generation
                   FROM ga_checks WHERE check_id=?""",
                (check_id,),
            ).fetchone()
            if row is None:
                raise KeyError(f"unknown check: {check_id}")
            actual = int(row[6])
            if actual != expected_generation:
                raise ValueError(
                    f"generation conflict: expected {expected_generation}, actual {actual}"
                )
            next_generation = actual + 1
            db.execute(
                """UPDATE ga_checks SET state=?,evidence_ref=?,generation=?
                   WHERE check_id=? AND generation=?""",
                (state, evidence_ref, next_generation, check_id, actual),
            )
        return GACheck(
            str(row[0]),
            str(row[1]),
            cast(EvidenceKind, str(row[2])),
            str(row[3]),
            state,
            evidence_ref,
            next_generation,
        )

    def register_compatibility(self, entry: GACompatibility) -> GACompatibility:
        self._required(entry.compatibility_id, "compatibility_id")
        self._required(entry.release_id, "release_id")
        self._required(entry.component, "component")
        self._required(entry.minimum_version, "minimum_version")
        with sqlite3.connect(self.store.path) as db:
            release = db.execute(
                "SELECT 1 FROM ga_releases WHERE release_id=?", (entry.release_id,)
            ).fetchone()
            if release is None:
                raise KeyError(f"unknown release: {entry.release_id}")
            db.execute(
                """INSERT INTO ga_compatibility
                (compatibility_id,release_id,component,minimum_version,maximum_version,
                 status,generation)
                VALUES (?,?,?,?,?,?,?)""",
                (
                    entry.compatibility_id,
                    entry.release_id,
                    entry.component,
                    entry.minimum_version,
                    entry.maximum_version,
                    entry.status,
                    entry.generation,
                ),
            )
        return entry

    def readiness(self, release_id: str) -> GAReadiness:
        self._required(release_id, "release_id")
        with sqlite3.connect(self.store.path) as db:
            release = db.execute(
                "SELECT 1 FROM ga_releases WHERE release_id=?", (release_id,)
            ).fetchone()
            if release is None:
                raise KeyError(f"unknown release: {release_id}")
            rows = db.execute(
                "SELECT state, COUNT(*) FROM ga_checks WHERE release_id=? GROUP BY state",
                (release_id,),
            ).fetchall()
        counts = {str(state): int(count) for state, count in rows}
        total = sum(counts.values())
        passed = counts.get("passed", 0)
        failed = counts.get("failed", 0)
        pending = counts.get("pending", 0)
        waived = counts.get("waived", 0)
        return GAReadiness(
            release_id,
            total > 0 and failed == 0 and pending == 0,
            total,
            passed,
            failed,
            pending,
            waived,
        )
