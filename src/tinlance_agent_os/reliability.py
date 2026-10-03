"""Reliability, HA, disaster-recovery and chaos contracts.

M38 describes enterprise deployment reliability without embedding a distributed
database or scheduler into the local Agent OS core. It records deployment
profiles, worker lease intent, DR plans and controlled chaos scenarios.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Final, Literal

from .store import StateStore

PersistenceMode = Literal["sqlite-local", "postgres-distributed"]
LeaseState = Literal["active", "expired", "released"]
DRState = Literal["planned", "tested", "failed", "ready"]
ChaosState = Literal["disabled", "enabled"]

_SCHEMA: Final[str] = """
CREATE TABLE IF NOT EXISTS reliability_profiles (
    profile_id TEXT PRIMARY KEY,
    workspace_id TEXT NOT NULL,
    persistence_mode TEXT NOT NULL CHECK(\n        persistence_mode IN ('sqlite-local','postgres-distributed')\n    ),
    regions INTEGER NOT NULL CHECK(regions >= 1),
    rpo_seconds INTEGER NOT NULL CHECK(rpo_seconds >= 0),
    rto_seconds INTEGER NOT NULL CHECK(rto_seconds >= 0),
    backups_required INTEGER NOT NULL CHECK(backups_required IN (0,1)),
    generation INTEGER NOT NULL CHECK(generation >= 0)
);

CREATE TABLE IF NOT EXISTS worker_leases (
    lease_id TEXT PRIMARY KEY,
    workspace_id TEXT NOT NULL,
    worker_id TEXT NOT NULL,
    resource TEXT NOT NULL,
    state TEXT NOT NULL CHECK(state IN ('active','expired','released')),
    expires_at TEXT NOT NULL,
    generation INTEGER NOT NULL CHECK(generation >= 0),
    UNIQUE(workspace_id, worker_id, resource)
);

CREATE TABLE IF NOT EXISTS dr_plans (
    plan_id TEXT PRIMARY KEY,
    workspace_id TEXT NOT NULL,
    backup_ref TEXT NOT NULL,
    restore_target TEXT NOT NULL,
    rpo_seconds INTEGER NOT NULL CHECK(rpo_seconds >= 0),
    rto_seconds INTEGER NOT NULL CHECK(rto_seconds >= 0),
    state TEXT NOT NULL CHECK(state IN ('planned','tested','failed','ready')),
    generation INTEGER NOT NULL CHECK(generation >= 0)
);

CREATE TABLE IF NOT EXISTS chaos_scenarios (
    scenario_id TEXT PRIMARY KEY,
    workspace_id TEXT NOT NULL,
    kind TEXT NOT NULL,
    blast_radius TEXT NOT NULL,
    state TEXT NOT NULL CHECK(state IN ('disabled','enabled')),
    generation INTEGER NOT NULL CHECK(generation >= 0)
);
"""


@dataclass(frozen=True, slots=True)
class ReliabilityProfile:
    profile_id: str
    workspace_id: str
    persistence_mode: PersistenceMode
    regions: int = 1
    rpo_seconds: int = 0
    rto_seconds: int = 0
    backups_required: bool = True
    generation: int = 0


@dataclass(frozen=True, slots=True)
class WorkerLease:
    lease_id: str
    workspace_id: str
    worker_id: str
    resource: str
    state: LeaseState
    expires_at: datetime
    generation: int = 0


@dataclass(frozen=True, slots=True)
class DRPlan:
    plan_id: str
    workspace_id: str
    backup_ref: str
    restore_target: str
    rpo_seconds: int
    rto_seconds: int
    state: DRState = "planned"
    generation: int = 0


@dataclass(frozen=True, slots=True)
class ChaosScenario:
    scenario_id: str
    workspace_id: str
    kind: str
    blast_radius: str
    state: ChaosState = "disabled"
    generation: int = 0


class ReliabilityRuntime:
    """Durable enterprise reliability deployment contract."""

    def __init__(self, store: StateStore) -> None:
        self.store = store
        with sqlite3.connect(store.path) as db:
            db.executescript(_SCHEMA)

    @staticmethod
    def _timestamp(value: datetime) -> datetime:
        if value.tzinfo is None:
            raise ValueError("timestamp must be timezone-aware")
        return value.astimezone(UTC)

    def register_profile(self, profile: ReliabilityProfile) -> ReliabilityProfile:
        if not profile.profile_id or not profile.workspace_id:
            raise ValueError("reliability profile identity is required")
        if profile.regions < 1 or profile.rpo_seconds < 0 or profile.rto_seconds < 0:
            raise ValueError("reliability targets must be non-negative")
        if profile.persistence_mode == "postgres-distributed" and profile.regions < 2:
            raise ValueError("distributed persistence requires at least two regions")
        with sqlite3.connect(self.store.path) as db:
            db.execute(
                """INSERT INTO reliability_profiles
                (profile_id,workspace_id,persistence_mode,regions,rpo_seconds,rto_seconds,
                 backups_required,generation)
                VALUES (?,?,?,?,?,?,?,?)""",
                (
                    profile.profile_id,
                    profile.workspace_id,
                    profile.persistence_mode,
                    profile.regions,
                    profile.rpo_seconds,
                    profile.rto_seconds,
                    int(profile.backups_required),
                    profile.generation,
                ),
            )
        return profile

    def acquire_lease(self, lease: WorkerLease) -> WorkerLease:
        if (\n            not lease.lease_id\n            or not lease.workspace_id\n            or not lease.worker_id\n            or not lease.resource\n        ):
            raise ValueError("lease identity is required")
        expires_at = self._timestamp(lease.expires_at)
        if expires_at <= datetime.now(UTC):
            raise ValueError("lease expiry must be in the future")
        with sqlite3.connect(self.store.path) as db:
            existing = db.execute(
                """SELECT lease_id,state,generation FROM worker_leases
                   WHERE workspace_id=? AND worker_id=? AND resource=?""",
                (lease.workspace_id, lease.worker_id, lease.resource),
            ).fetchone()
            if existing is not None and str(existing[1]) == "active":
                raise ValueError("active lease already exists")
            generation = 0 if existing is None else int(existing[2]) + 1
            db.execute(
                """INSERT INTO worker_leases
                (lease_id,workspace_id,worker_id,resource,state,expires_at,generation)
                VALUES (?,?,?,?,?,?,?)
                ON CONFLICT(workspace_id,worker_id,resource) DO UPDATE SET
                  lease_id=excluded.lease_id,
                  state=excluded.state,
                  expires_at=excluded.expires_at,
                  generation=excluded.generation""",
                (
                    lease.lease_id,
                    lease.workspace_id,
                    lease.worker_id,
                    lease.resource,
                    "active",
                    expires_at.isoformat(),
                    generation,
                ),
            )
        return WorkerLease(
            lease.lease_id,
            lease.workspace_id,
            lease.worker_id,
            lease.resource,
            "active",
            expires_at,
            generation,
        )

    def release_lease(self, lease_id: str, *, expected_generation: int) -> WorkerLease:
        with sqlite3.connect(self.store.path) as db:
            row = db.execute(
                """SELECT lease_id,workspace_id,worker_id,resource,state,expires_at,generation
                   FROM worker_leases WHERE lease_id=?""",
                (lease_id,),
            ).fetchone()
            if row is None:
                raise KeyError(f"unknown lease: {lease_id}")
            actual = int(row[6])
            if actual != expected_generation:
                raise ValueError(
                    f"generation conflict: expected {expected_generation}, actual {actual}"
                )
            next_generation = actual + 1
            db.execute(
                "UPDATE worker_leases SET state='released',generation=? WHERE lease_id=?",
                (next_generation, lease_id),
            )
        return WorkerLease(
            str(row[0]),
            str(row[1]),
            str(row[2]),
            str(row[3]),
            "released",
            datetime.fromisoformat(str(row[5])),
            next_generation,
        )

    def register_dr_plan(self, plan: DRPlan) -> DRPlan:
        if not plan.plan_id or not plan.workspace_id or not plan.backup_ref:
            raise ValueError("DR plan identity is required")
        if not plan.restore_target:
            raise ValueError("restore target is required")
        if plan.rpo_seconds < 0 or plan.rto_seconds < 0:
            raise ValueError("DR targets must be non-negative")
        with sqlite3.connect(self.store.path) as db:
            db.execute(
                """INSERT INTO dr_plans
                (plan_id,workspace_id,backup_ref,restore_target,rpo_seconds,rto_seconds,state,generation)
                VALUES (?,?,?,?,?,?,?,?)""",
                (
                    plan.plan_id,
                    plan.workspace_id,
                    plan.backup_ref,
                    plan.restore_target,
                    plan.rpo_seconds,
                    plan.rto_seconds,
                    plan.state,
                    plan.generation,
                ),
            )
        return plan

    def register_chaos(self, scenario: ChaosScenario) -> ChaosScenario:
        if not scenario.scenario_id or not scenario.workspace_id or not scenario.kind:
            raise ValueError("chaos scenario identity is required")
        if not scenario.blast_radius:
            raise ValueError("blast_radius is required")
        with sqlite3.connect(self.store.path) as db:
            db.execute(
                """INSERT INTO chaos_scenarios
                (scenario_id,workspace_id,kind,blast_radius,state,generation)
                VALUES (?,?,?,?,?,?)""",
                (
                    scenario.scenario_id,
                    scenario.workspace_id,
                    scenario.kind,
                    scenario.blast_radius,
                    scenario.state,
                    scenario.generation,
                ),
            )
        return scenario

    def readiness(self, workspace_id: str) -> dict[str, bool]:
        if not workspace_id:
            raise ValueError("workspace_id is required")
        with sqlite3.connect(self.store.path) as db:
            profile = db.execute(
                """SELECT persistence_mode,regions,rpo_seconds,rto_seconds,backups_required
                   FROM reliability_profiles
                   WHERE workspace_id=? ORDER BY generation DESC LIMIT 1""",
                (workspace_id,),
            ).fetchone()
            dr = db.execute(
                "SELECT COUNT(*) FROM dr_plans "
                "WHERE workspace_id=? AND state IN ('tested','ready')",
                (workspace_id,),
            ).fetchone()
            chaos = db.execute(
                "SELECT COUNT(*) FROM chaos_scenarios WHERE workspace_id=? AND state='enabled'",
                (workspace_id,),
            ).fetchone()
        return {
            "profile_present": profile is not None,
            "distributed_ready": profile is not None
            and (
                str(profile[0]) == "sqlite-local"
                or int(profile[1]) >= 2
            ),
            "targets_defined": profile is not None
            and int(profile[2]) >= 0
            and int(profile[3]) >= 0,
            "backup_required": bool(profile and profile[4]),
            "dr_tested": bool(dr and int(dr[0]) > 0),
            "chaos_enabled": bool(chaos and int(chaos[0]) > 0),
        }
