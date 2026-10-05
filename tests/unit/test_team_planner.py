from tinlance_agent_os.team_planner import compose_spec, plan
from tinlance_agent_os.team_spec import TeamBudget, TeamTopology


def test_planner_prefers_single_agent() -> None:
    result = plan("research goal", ("a",), 3, TeamBudget(max_agents=3, max_active_agents=3))
    assert result.topology is TeamTopology.SINGLE
    assert result.goal == "research goal"


def test_planner_parallelizes_distinct_capabilities() -> None:
    result = plan("research goal", ("a", "b"), 2, TeamBudget(max_agents=2, max_active_agents=2))
    assert result.topology is TeamTopology.PARALLEL


def test_compose_spec_preserves_goal() -> None:
    result = plan("original goal", ("a", "b"), 2, TeamBudget(max_agents=2, max_active_agents=2))
    spec = compose_spec(result, "team-1", "workspace-1", "supervisor-1", ("a", "b"), TeamBudget(max_agents=2, max_active_agents=2))
    assert spec.goal == "original goal"
