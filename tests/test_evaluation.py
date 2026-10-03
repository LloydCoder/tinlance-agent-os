from __future__ import annotations

import sqlite3
from datetime import UTC, datetime
from pathlib import Path

import pytest

from tinlance_agent_os.evaluation import (
    EvaluationCase,
    EvaluationGate,
    EvaluationMeasurement,
    EvaluationRun,
    EvaluationRuntime,
)
from tinlance_agent_os.store import StateStore


def make_runtime(tmp_path: Path) -> EvaluationRuntime:
    return EvaluationRuntime(StateStore(tmp_path / "state.db"))


def test_evaluation_is_durable_and_gateable(tmp_path: Path) -> None:
    runtime = make_runtime(tmp_path)
    runtime.register_case(
        EvaluationCase("case-1", "suite-1", "baseline", "1", "sha256:input")
    )
    runtime.start_run(
        EvaluationRun(
            "run-1",
            "suite-1",
            "workspace-1",
            started_at=datetime(2026, 10, 3, tzinfo=UTC),
        )
    )
    runtime.record_measurement(
        EvaluationMeasurement(
            "measurement-1", "run-1", "case-1", "success_rate_bps", 9800, "bps"
        )
    )
    runtime.register_gate(
        EvaluationGate("gate-1", "suite-1", "success_rate_bps", "min", 9500, "bps")
    )
    assert runtime.evaluate_gates("run-1")[0].passed is True


def test_gate_fails_closed_on_missing_or_wrong_unit(tmp_path: Path) -> None:
    runtime = make_runtime(tmp_path)
    runtime.register_case(EvaluationCase("case-1", "suite-1", "case", "1", "digest"))
    runtime.start_run(EvaluationRun("run-1", "suite-1", "workspace-1"))
    runtime.register_gate(
        EvaluationGate("gate-1", "suite-1", "success_rate_bps", "min", 9500, "bps")
    )
    assert runtime.evaluate_gates("run-1")[0].passed is False
    runtime.record_measurement(
        EvaluationMeasurement("measurement-1", "run-1", "case-1", "success_rate_bps", 9900, "ratio")
    )
    assert runtime.evaluate_gates("run-1")[0].passed is False


def test_duplicate_measurement_and_naive_timestamp_fail_closed(tmp_path: Path) -> None:
    runtime = make_runtime(tmp_path)
    runtime.register_case(EvaluationCase("case-1", "suite-1", "case", "1", "digest"))
    runtime.start_run(EvaluationRun("run-1", "suite-1", "workspace-1"))
    measurement = EvaluationMeasurement(
        "measurement-1",
        "run-1",
        "case-1",
        "latency",
        100,
        "ms",
        datetime(2026, 10, 3, tzinfo=UTC),
    )
    runtime.record_measurement(measurement)
    with pytest.raises(sqlite3.IntegrityError):
        runtime.record_measurement(measurement)
    with pytest.raises(ValueError, match="timezone-aware"):
        runtime.record_measurement(
            EvaluationMeasurement(
                "measurement-2",
                "run-1",
                "case-1",
                "latency",
                100,
                "ms",
                datetime(2026, 10, 3),
            )
        )


def test_run_comparison_is_deterministic(tmp_path: Path) -> None:
    runtime = make_runtime(tmp_path)
    runtime.register_case(EvaluationCase("case-1", "suite-1", "case", "1", "digest"))
    for run_id, value in (("baseline", 9000), ("candidate", 9400)):
        runtime.start_run(EvaluationRun(run_id, "suite-1", "workspace-1"))
        runtime.record_measurement(
            EvaluationMeasurement(
                f"{run_id}-measurement",
                run_id,
                "case-1",
                "success_rate_bps",
                value,
                "bps",
            )
        )
    assert runtime.compare_runs("baseline", "candidate") == {"success_rate_bps": 400}
