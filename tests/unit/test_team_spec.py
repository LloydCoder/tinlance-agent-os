import pytest

from tinlance_agent_os.team_spec import TeamBudget, TeamSpec, TeamTopology


def test_team_spec_is_bounded() -> None:
    spec = TeamSpec(
        "t",
        "goal",
        "w",
        "sup",
        ("a", "b"),
        TeamTopology.PARALLEL,
        TeamBudget(max_agents=2, max_active_agents=2, max_fanout=2),
    )
    assert spec.failure_policy == "fail_closed"


def test_team_budget_rejects_excess_active_agents() -> None:
    with pytest.raises(ValueError, match="max_active_agents"):
        TeamBudget(max_agents=1, max_active_agents=2)
