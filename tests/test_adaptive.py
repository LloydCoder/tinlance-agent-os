from __future__ import annotations

from pathlib import Path

import pytest

from tinlance_agent_os.adaptive import (
    AdaptiveObservation,
    AdaptivePolicy,
    AdaptiveRuntime,
)
from tinlance_agent_os.store import StateStore


def make_runtime(tmp_path: Path) -> AdaptiveRuntime:
    return AdaptiveRuntime(StateStore(tmp_path / "state.db"))


def test_adaptive_recommendation_is_deterministic_and_workspace_scoped(tmp_path: Path) -> None:
    runtime = make_runtime(tmp_path)
    runtime.register_policy(
        AdaptivePolicy("latency-1", "workspace-1", "latency", "p95_latency_ms", 500, 25)
    )
    observation = AdaptiveObservation("obs-1", "workspace-1", "latency-1", 650, "ms", 100)
    runtime.record_observation(observation)
    recommendation = runtime.recommend(
        observation,
        recommendation_id="rec-1",
        strategy="model_route",
        action_ref="model-router/profile-a",
    )
    assert recommendation is not None
    assert recommendation.state == "proposed"
    assert "above target" in recommendation.reason
    assert (
        runtime.recommend(
            AdaptiveObservation("obs-2", "workspace-1", "latency-1", 510, "ms", 100),
            recommendation_id="rec-2",
            strategy="model_route",
            action_ref="model-router/profile-b",
        )
        is None
    )


def test_adaptive_decision_requires_generation(tmp_path: Path) -> None:
    runtime = make_runtime(tmp_path)
    runtime.register_policy(AdaptivePolicy("cost-1", "workspace-1", "cost", "cost_micro", 100, 0))
    observation = AdaptiveObservation("obs-1", "workspace-1", "cost-1", 125, "micro", 10)
    runtime.record_observation(observation)
    runtime.recommend(
        observation,
        recommendation_id="rec-1",
        strategy="resource_route",
        action_ref="capacity/profile-a",
    )
    with pytest.raises(ValueError, match="generation conflict"):
        runtime.decide("rec-1", accepted=True, expected_generation=9)
    decided = runtime.decide("rec-1", accepted=True, expected_generation=0)
    assert decided.state == "accepted"
    assert decided.generation == 1


def test_adaptive_rejects_cross_workspace_observations(tmp_path: Path) -> None:
    runtime = make_runtime(tmp_path)
    runtime.register_policy(
        AdaptivePolicy("quality-1", "workspace-1", "quality", "success_rate", 0.9, 0.01)
    )
    observation = AdaptiveObservation("obs-1", "workspace-2", "quality-1", 0.5, "ratio", 20)
    with pytest.raises(ValueError, match="workspace mismatch"):
        runtime.record_observation(observation)
