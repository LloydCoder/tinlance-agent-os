from tinlance_agent_os.team_planner import plan
from tinlance_agent_os.team_spec import TeamBudget, TeamTopology


def test_planner_prefers_single_agent() -> None:
    result = plan("x", ("a",), 3, TeamBudget(max_agents=3, max_active_agents=3))
    assert result.topology is TeamTopology.SINGLE


def test_planner_parallelizes_distinct_capabilities() -> None:
    result = plan("x", ("a", "b"), 2, TeamBudget(max_agents=2, max_active_agents=2))
    assert result.topology is TeamTopology.PARALLEL
