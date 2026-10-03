"""Agent quality and evaluation runtime for Tinlance Agent OS.

M33 owns evaluation lifecycle, durable results, deterministic metric records,
regression gates and comparison metadata. It does not authorize execution,
grant capabilities, or treat evaluation output as Platform authority.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Final, Literal

from .store import StateStore

MetricDirection = Literal["min", "max"]

_SCHEMA: Final = """
CREATE TABLE IF NOT EXISTS evaluation_cases (
    case_id TEXT PRIMARY KEY,
    suite_id TEXT NOT NULL,
    name TEXT NOT NULL,
    version TEXT NOT NULL,
    input_digest TEXT NOT NULL,
    expected_digest TEXT,
    enabled INTEGER NOT NULL CHECK(enabled IN (0,1))
);
CREATE INDEX IF NOT EXISTS idx_evaluation_cases_suite
    ON evaluation_cases(suite_id, case_id);

CREATE TABLE IF NOT EXISTS evaluation_runs (
    run_id TEXT PRIMARY KEY,
    suite_id TEXT NOT NULL,
    workspace_id TEXT NOT NULL,
    agent_id TEXT,
    workflow_id TEXT,
    model TEXT,
    status TEXT NOT NULL,
    started_at TEXT NOT NULL,
    completed_at TEXT
);
CREATE INDEX IF NOT EXISTS idx_evaluation_runs_suite
    ON evaluation_runs(suite_id, started_at);

CREATE TABLE IF NOT EXISTS evaluation_measurements (
    measurement_id TEXT PRIMARY KEY,
    run_id TEXT NOT NULL REFERENCES evaluation_runs(run_id),
    case_id TEXT NOT NULL REFERENCES evaluation_cases(case_id),
    metric TEXT NOT NULL,
    value INTEGER NOT NULL,
    unit TEXT NOT NULL,
    observed_at TEXT NOT NULL,
    evidence_ref TEXT,
    UNIQUE(run_id, case_id, metric)
);
CREATE INDEX IF NOT EXISTS idx_evaluation_measurements_run
    ON evaluation_measurements(run_id, metric);

CREATE TABLE IF NOT EXISTS evaluation_gates (
    gate_id TEXT PRIMARY KEY,
    suite_id TEXT NOT NULL,
    metric TEXT NOT NULL,
    direction TEXT NOT NULL CHECK(direction IN ('min','max')),
    threshold INTEGER NOT NULL,
    unit TEXT NOT NULL,
    enabled INTEGER NOT NULL CHECK(enabled IN (0,1))
);
CREATE INDEX IF NOT EXISTS idx_evaluation_gates_suite
    ON evaluation_gates(suite_id, metric);
"""


@dataclass(frozen=True, slots=True)
class EvaluationCase:
    case_id: str
    suite_id: str
    name: str
    version: str
    input_digest: str
    expected_digest: str | None = None
    enabled: bool = True


@dataclass(frozen=True, slots=True)
class EvaluationRun:
    run_id: str
    suite_id: str
    workspace_id: str
    agent_id: str | None = None
    workflow_id: str | None = None
    model: str | None = None
    status: str = "running"
    started_at: datetime | None = None
    completed_at: datetime | None = None


@dataclass(frozen=True, slots=True)
class EvaluationMeasurement:
    measurement_id: str
    run_id: str
    case_id: str
    metric: str
    value: int
    unit: str
    observed_at: datetime | None = None
    evidence_ref: str | None = None


@dataclass(frozen=True, slots=True)
class EvaluationGate:
    gate_id: str
    suite_id: str
    metric: str
    direction: MetricDirection
    threshold: int
    unit: str
    enabled: bool = True


@dataclass(frozen=True, slots=True)
class GateResult:
    gate_id: str
    metric: str
    threshold: int
    observed: int | None
    unit: str
    passed: bool


class EvaluationRuntime:
    """Durable evaluation records and deterministic regression gates."""

    def __init__(self, store: StateStore) -> None:
        self.store = store
        with sqlite3.connect(store.path) as db:
            db.executescript(_SCHEMA)

    @staticmethod
    def _timestamp(value: datetime | None) -> datetime:
        value = value or datetime.now(UTC)
        if value.tzinfo is None:
            raise ValueError("timestamp must be timezone-aware")
        return value.astimezone(UTC)

    def register_case(self, case: EvaluationCase) -> EvaluationCase:
        if not case.case_id or not case.suite_id or not case.name:
            raise ValueError("case identity is required")
        if not case.version or not case.input_digest:
            raise ValueError("case version and input_digest are required")
        with sqlite3.connect(self.store.path) as db:
            db.execute(
                """INSERT INTO evaluation_cases
                (case_id,suite_id,name,version,input_digest,expected_digest,enabled)
                VALUES (?,?,?,?,?,?,?)""",
                (
                    case.case_id,
                    case.suite_id,
                    case.name,
                    case.version,
                    case.input_digest,
                    case.expected_digest,
                    int(case.enabled),
                ),
            )
        return case

    def start_run(self, run: EvaluationRun) -> EvaluationRun:
        if not run.run_id or not run.suite_id or not run.workspace_id:
            raise ValueError("run identity is required")
        started_at = self._timestamp(run.started_at)
        normalized = EvaluationRun(
            run.run_id,
            run.suite_id,
            run.workspace_id,
            run.agent_id,
            run.workflow_id,
            run.model,
            run.status,
            started_at,
            run.completed_at,
        )
        with sqlite3.connect(self.store.path) as db:
            db.execute(
                """INSERT INTO evaluation_runs
                (run_id,suite_id,workspace_id,agent_id,workflow_id,model,status,started_at,completed_at)
                VALUES (?,?,?,?,?,?,?,?,?)""",
                (
                    normalized.run_id,
                    normalized.suite_id,
                    normalized.workspace_id,
                    normalized.agent_id,
                    normalized.workflow_id,
                    normalized.model,
                    normalized.status,
                    normalized.started_at.isoformat(),
                    normalized.completed_at.isoformat()
                    if normalized.completed_at
                    else None,
                ),
            )
        return normalized

    def finish_run(
        self,
        run_id: str,
        *,
        status: str = "completed",
        completed_at: datetime | None = None,
    ) -> None:
        if not run_id or not status:
            raise ValueError("run_id and status are required")
        completed = self._timestamp(completed_at)
        with sqlite3.connect(self.store.path) as db:
            updated = db.execute(
                "UPDATE evaluation_runs SET status=?, completed_at=? WHERE run_id=?",
                (status, completed.isoformat(), run_id),
            ).rowcount
        if updated != 1:
            raise KeyError(f"unknown evaluation run: {run_id}")

    def record_measurement(
        self, measurement: EvaluationMeasurement
    ) -> EvaluationMeasurement:
        if not measurement.measurement_id or not measurement.metric:
            raise ValueError("measurement identity is required")
        if measurement.unit == "":
            raise ValueError("measurement unit is required")
        observed_at = self._timestamp(measurement.observed_at)
        normalized = EvaluationMeasurement(
            measurement.measurement_id,
            measurement.run_id,
            measurement.case_id,
            measurement.metric,
            measurement.value,
            measurement.unit,
            observed_at,
            measurement.evidence_ref,
        )
        with sqlite3.connect(self.store.path) as db:
            run = db.execute(
                "SELECT suite_id FROM evaluation_runs WHERE run_id=?", (normalized.run_id,)
            ).fetchone()
            case = db.execute(
                "SELECT suite_id FROM evaluation_cases WHERE case_id=?", (normalized.case_id,)
            ).fetchone()
            if run is None:
                raise KeyError(f"unknown evaluation run: {normalized.run_id}")
            if case is None:
                raise KeyError(f"unknown evaluation case: {normalized.case_id}")
            if str(run[0]) != str(case[0]):
                raise ValueError("evaluation case and run must belong to the same suite")
            db.execute(
                """INSERT INTO evaluation_measurements
                (measurement_id,run_id,case_id,metric,value,unit,observed_at,evidence_ref)
                VALUES (?,?,?,?,?,?,?,?)""",
                (
                    normalized.measurement_id,
                    normalized.run_id,
                    normalized.case_id,
                    normalized.metric,
                    normalized.value,
                    normalized.unit,
                    normalized.observed_at.isoformat(),
                    normalized.evidence_ref,
                ),
            )
        return normalized

    def register_gate(self, gate: EvaluationGate) -> EvaluationGate:
        if not gate.gate_id or not gate.suite_id or not gate.metric:
            raise ValueError("gate identity is required")
        if not gate.unit:
            raise ValueError("gate unit is required")
        with sqlite3.connect(self.store.path) as db:
            db.execute(
                """INSERT INTO evaluation_gates
                (gate_id,suite_id,metric,direction,threshold,unit,enabled)
                VALUES (?,?,?,?,?,?,?)""",
                (
                    gate.gate_id,
                    gate.suite_id,
                    gate.metric,
                    gate.direction,
                    gate.threshold,
                    gate.unit,
                    int(gate.enabled),
                ),
            )
        return gate

    def evaluate_gates(self, run_id: str) -> list[GateResult]:
        with sqlite3.connect(self.store.path) as db:
            run = db.execute(
                "SELECT suite_id FROM evaluation_runs WHERE run_id=?", (run_id,)
            ).fetchone()
            if run is None:
                raise KeyError(f"unknown evaluation run: {run_id}")
            suite_id = str(run[0])
            gates = db.execute(
                """SELECT gate_id,metric,direction,threshold,unit
                   FROM evaluation_gates
                   WHERE suite_id=? AND enabled=1 ORDER BY gate_id""",
                (suite_id,),
            ).fetchall()
            results: list[GateResult] = []
            for gate_id, metric, direction, threshold, unit in gates:
                row = db.execute(
                    """SELECT AVG(value), COUNT(DISTINCT unit), MIN(unit)
                       FROM evaluation_measurements
                       WHERE run_id=? AND metric=?""",
                    (run_id, metric),
                ).fetchone()
                observed = None if row[0] is None else int(row[0])
                unit_count = int(row[1] or 0)
                observed_unit = None if row[2] is None else str(row[2])
                unit_matches = (
                    observed is not None
                    and unit_count == 1
                    and observed_unit == unit
                )
                passed = (
                    observed is not None
                    and unit_matches
                    and (
                        observed >= threshold
                        if direction == "min"
                        else observed <= threshold
                    )
                )
                results.append(
                    GateResult(
                        str(gate_id),
                        str(metric),
                        int(threshold),
                        observed,
                        unit,
                        passed,
                    )
                )
        return results

    def compare_runs(
        self,
        baseline_run_id: str,
        candidate_run_id: str,
    ) -> dict[str, int]:
        with sqlite3.connect(self.store.path) as db:
            suites = db.execute(
                """SELECT DISTINCT suite_id FROM evaluation_runs
                   WHERE run_id IN (?,?) ORDER BY suite_id""",
                (baseline_run_id, candidate_run_id),
            ).fetchall()
            if len(suites) != 1:
                raise ValueError("baseline and candidate runs must belong to one suite")
            rows = db.execute(
                """SELECT metric,
                          AVG(CASE WHEN run_id=? THEN value END),
                          AVG(CASE WHEN run_id=? THEN value END),
                          COUNT(DISTINCT CASE WHEN run_id=? THEN unit END),
                          COUNT(DISTINCT CASE WHEN run_id=? THEN unit END),
                          MIN(CASE WHEN run_id=? THEN unit END),
                          MIN(CASE WHEN run_id=? THEN unit END)
                   FROM evaluation_measurements
                   WHERE run_id IN (?,?)
                   GROUP BY metric ORDER BY metric""",
                (
                    baseline_run_id,
                    candidate_run_id,
                    baseline_run_id,
                    candidate_run_id,
                    baseline_run_id,
                    candidate_run_id,
                    baseline_run_id,
                    candidate_run_id,
                ),
            ).fetchall()
        comparison: dict[str, int] = {}
        for (
            metric,
            baseline,
            candidate,
            baseline_units,
            candidate_units,
            baseline_unit,
            candidate_unit,
        ) in rows:
            if (
                baseline is None
                or candidate is None
                or int(baseline_units) != 1
                or int(candidate_units) != 1
                or baseline_unit != candidate_unit
            ):
                continue
            comparison[str(metric)] = int(candidate) - int(baseline)
        return comparison
