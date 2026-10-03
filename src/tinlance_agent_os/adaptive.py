"""Adaptive Agent OS runtime contracts.

M40 turns observed runtime telemetry into durable, explainable recommendations.
It deliberately stops at recommendation/intent: consequential execution,
capability grants, budgets, approvals and evidence remain outside this module
and authoritative in Agent Platform or the owning runtime.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from typing import Final, Literal

from .store import StateStore

Objective = Literal["latency", "cost", "reliability", "capacity", "quality"]
RecommendationState = Literal["proposed", "accepted", "rejected", "expired"]
Strategy = Literal[
    "model_route",
    "workflow_route",
    "context_optimize",
    "resource_route",
    "fleet_place",
    "retry_tune",
    "remediation",
]


_SCHEMA: Final = """
CREATE TABLE IF NOT EXISTS adaptive_policies (
    policy_id TEXT PRIMARY KEY,
    workspace_id TEXT NOT NULL,
    objective TEXT NOT NULL CHECK(
        objective IN ('latency','cost','reliability','capacity','quality')
    ),
    metric TEXT NOT NULL,
    target REAL NOT NULL,
    tolerance REAL NOT NULL CHECK(tolerance >= 0),
    generation INTEGER NOT NULL CHECK(generation >= 0)
);

CREATE TABLE IF NOT EXISTS adaptive_observations (
    observation_id TEXT PRIMARY KEY,
    workspace_id TEXT NOT NULL,
    policy_id TEXT NOT NULL,
    value REAL NOT NULL,
    unit TEXT NOT NULL,
    sample_size INTEGER NOT NULL CHECK(sample_size >= 1),
    generation INTEGER NOT NULL CHECK(generation >= 0)
);

CREATE TABLE IF NOT EXISTS adaptive_recommendations (
    recommendation_id TEXT PRIMARY KEY,
    workspace_id TEXT NOT NULL,
    policy_id TEXT NOT NULL,
    strategy TEXT NOT NULL CHECK(
        strategy IN (
            'model_route','workflow_route','context_optimize',
            'resource_route','fleet_place','retry_tune','remediation'
        )
    ),
    action_ref TEXT NOT NULL,
    reason TEXT NOT NULL,
    observed_value REAL NOT NULL,
    target_value REAL NOT NULL,
    state TEXT NOT NULL CHECK(
        state IN ('proposed','accepted','rejected','expired')
    ),
    generation INTEGER NOT NULL CHECK(generation >= 0)
);
"""


@dataclass(frozen=True, slots=True)
class AdaptivePolicy:
    policy_id: str
    workspace_id: str
    objective: Objective
    metric: str
    target: float
    tolerance: float
    generation: int = 0


@dataclass(frozen=True, slots=True)
class AdaptiveObservation:
    observation_id: str
    workspace_id: str
    policy_id: str
    value: float
    unit: str
    sample_size: int
    generation: int = 0


@dataclass(frozen=True, slots=True)
class AdaptiveRecommendation:
    recommendation_id: str
    workspace_id: str
    policy_id: str
    strategy: Strategy
    action_ref: str
    reason: str
    observed_value: float
    target_value: float
    state: RecommendationState = "proposed"
    generation: int = 0


class AdaptiveRuntime:
    """Durable, explainable optimization intent above governed execution."""

    def __init__(self, store: StateStore) -> None:
        self.store = store
        with sqlite3.connect(store.path) as db:
            db.executescript(_SCHEMA)

    @staticmethod
    def _required(value: str, label: str) -> None:
        if not value.strip():
            raise ValueError(f"{label} is required")

    def register_policy(self, policy: AdaptivePolicy) -> AdaptivePolicy:
        self._required(policy.policy_id, "policy_id")
        self._required(policy.workspace_id, "workspace_id")
        self._required(policy.metric, "metric")
        if policy.tolerance < 0:
            raise ValueError("tolerance must be non-negative")
        with sqlite3.connect(self.store.path) as db:
            db.execute(
                """INSERT INTO adaptive_policies
                (policy_id,workspace_id,objective,metric,target,tolerance,generation)
                VALUES (?,?,?,?,?,?,?)""",
                (
                    policy.policy_id,
                    policy.workspace_id,
                    policy.objective,
                    policy.metric,
                    policy.target,
                    policy.tolerance,
                    policy.generation,
                ),
            )
        return policy

    def record_observation(self, observation: AdaptiveObservation) -> AdaptiveObservation:
        self._required(observation.observation_id, "observation_id")
        self._required(observation.workspace_id, "workspace_id")
        self._required(observation.policy_id, "policy_id")
        self._required(observation.unit, "unit")
        if observation.sample_size < 1:
            raise ValueError("sample_size must be at least one")
        with sqlite3.connect(self.store.path) as db:
            policy = db.execute(
                "SELECT workspace_id FROM adaptive_policies WHERE policy_id=?",
                (observation.policy_id,),
            ).fetchone()
            if policy is None:
                raise KeyError(f"unknown adaptive policy: {observation.policy_id}")
            if str(policy[0]) != observation.workspace_id:
                raise ValueError("policy and observation workspace mismatch")
            db.execute(
                """INSERT INTO adaptive_observations
                (observation_id,workspace_id,policy_id,value,unit,sample_size,generation)
                VALUES (?,?,?,?,?,?,?)""",
                (
                    observation.observation_id,
                    observation.workspace_id,
                    observation.policy_id,
                    observation.value,
                    observation.unit,
                    observation.sample_size,
                    observation.generation,
                ),
            )
        return observation

    def recommend(
        self,
        observation: AdaptiveObservation,
        *,
        recommendation_id: str,
        strategy: Strategy,
        action_ref: str,
    ) -> AdaptiveRecommendation | None:
        self._required(recommendation_id, "recommendation_id")
        self._required(action_ref, "action_ref")
        with sqlite3.connect(self.store.path) as db:
            row = db.execute(
                """SELECT objective,metric,target,tolerance,workspace_id
                   FROM adaptive_policies WHERE policy_id=?""",
                (observation.policy_id,),
            ).fetchone()
            if row is None:
                raise KeyError(f"unknown adaptive policy: {observation.policy_id}")
        objective, metric, target, tolerance, workspace_id = row
        if str(workspace_id) != observation.workspace_id:
            raise ValueError("policy and observation workspace mismatch")
        deviation = float(observation.value) - float(target)
        needs_action = abs(deviation) > float(tolerance)
        if not needs_action:
            return None
        direction = "above" if deviation > 0 else "below"
        reason = (
            f"{metric} is {direction} target by "
            f"{abs(deviation):g} {observation.unit}; objective={objective}"
        )
        recommendation = AdaptiveRecommendation(
            recommendation_id,
            observation.workspace_id,
            observation.policy_id,
            strategy,
            action_ref,
            reason,
            observation.value,
            float(target),
        )
        with sqlite3.connect(self.store.path) as db:
            db.execute(
                """INSERT INTO adaptive_recommendations
                (recommendation_id,workspace_id,policy_id,strategy,action_ref,reason,
                 observed_value,target_value,state,generation)
                VALUES (?,?,?,?,?,?,?,?,?,?)""",
                (
                    recommendation.recommendation_id,
                    recommendation.workspace_id,
                    recommendation.policy_id,
                    recommendation.strategy,
                    recommendation.action_ref,
                    recommendation.reason,
                    recommendation.observed_value,
                    recommendation.target_value,
                    recommendation.state,
                    recommendation.generation,
                ),
            )
        return recommendation

    def decide(
        self,
        recommendation_id: str,
        *,
        accepted: bool,
        expected_generation: int,
    ) -> AdaptiveRecommendation:
        with sqlite3.connect(self.store.path) as db:
            row = db.execute(
                """SELECT recommendation_id,workspace_id,policy_id,strategy,action_ref,
                          reason,observed_value,target_value,state,generation
                   FROM adaptive_recommendations WHERE recommendation_id=?""",
                (recommendation_id,),
            ).fetchone()
            if row is None:
                raise KeyError(f"unknown recommendation: {recommendation_id}")
            actual = int(row[9])
            if actual != expected_generation:
                raise ValueError(
                    f"generation conflict: expected {expected_generation}, actual {actual}"
                )
            state: RecommendationState = "accepted" if accepted else "rejected"
            next_generation = actual + 1
            db.execute(
                """UPDATE adaptive_recommendations
                   SET state=?, generation=?
                   WHERE recommendation_id=? AND generation=?""",
                (state, next_generation, recommendation_id, actual),
            )
        return AdaptiveRecommendation(
            str(row[0]), str(row[1]), str(row[2]), str(row[3]), str(row[4]),
            str(row[5]), float(row[6]), float(row[7]), state, next_generation
        )

    def recommendations(self, workspace_id: str) -> tuple[AdaptiveRecommendation, ...]:
        self._required(workspace_id, "workspace_id")
        with sqlite3.connect(self.store.path) as db:
            rows = db.execute(
                """SELECT recommendation_id,workspace_id,policy_id,strategy,action_ref,
                          reason,observed_value,target_value,state,generation
                   FROM adaptive_recommendations
                   WHERE workspace_id=? ORDER BY recommendation_id""",
                (workspace_id,),
            ).fetchall()
        return tuple(
            AdaptiveRecommendation(
                str(r[0]), str(r[1]), str(r[2]), str(r[3]), str(r[4]),
                str(r[5]), float(r[6]), float(r[7]), str(r[8]), int(r[9])
            )
            for r in rows
        )
