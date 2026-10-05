"""Explainable dynamic team planning."""

from __future__ import annotations

from dataclasses import dataclass

from .team_spec import TeamBudget, TeamSpec, TeamTopology


@dataclass(frozen=True, slots=True)
class GoalPlan:
    topology: TeamTopology
    required_capabilities: tuple[str, ...]
    rationale: tuple[str, ...]


def plan(
    goal: str,
    capabilities: tuple[str, ...],
    candidates: int,
    budget: TeamBudget,
) -> GoalPlan:
    if not goal.strip():
        raise ValueError("goal required")
    if not capabilities:
        raise ValueError("capabilities required")
    if candidates <= 1:
        return GoalPlan(
            TeamTopology.SINGLE,
            capabilities,
            ("one capable candidate is sufficient",),
        )
    if len(capabilities) == 1:
        return GoalPlan(
            TeamTopology.SINGLE,
            capabilities,
            ("single capability does not warrant collaboration",),
        )
    topology = (
        TeamTopology.PARALLEL
        if budget.max_active_agents > 1
        else TeamTopology.SEQUENTIAL
    )
    return GoalPlan(
        topology,
        capabilities,
        ("multiple independent capability requirements",),
    )


def compose_spec(
    goal_plan: GoalPlan,
    team_id: str,
    workspace: str,
    supervisor: str,
    members: tuple[str, ...],
    budget: TeamBudget,
) -> TeamSpec:
    return TeamSpec(
        team_id,
        goal_plan.rationale[0] if goal_plan.rationale else goal_plan.topology.value,
        workspace,
        supervisor,
        members,
        goal_plan.topology,
        budget,
    )
