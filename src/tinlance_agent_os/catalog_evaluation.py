"""Catalog/team evaluation primitives."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class EvaluationMeasurement:
    metric: str
    value: float
    passed: bool


@dataclass(frozen=True, slots=True)
class CatalogEvaluation:
    case_id: str
    measurements: tuple[EvaluationMeasurement, ...]

    @property
    def passed(self) -> bool:
        return all(measurement.passed for measurement in self.measurements)


def evaluate(
    case_id: str,
    expected: dict[str, float],
    actual: dict[str, float],
    tolerance: float = 0.0,
) -> CatalogEvaluation:
    measurements = tuple(
        EvaluationMeasurement(
            metric,
            float(actual.get(metric, 0)),
            metric in actual and abs(actual[metric] - expected_value) <= tolerance,
        )
        for metric, expected_value in expected.items()
    )
    return CatalogEvaluation(case_id, measurements)
