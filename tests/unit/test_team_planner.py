from tinlance_agent_os.team_planner import plan
from tinlance_agent_os.team_spec import TeamBudget,TeamTopology
def test_planner_prefers_single_agent():
 assert plan("x",("a",),3,TeamBudget(max_active_agents=3)).topology is TeamTopology.SINGLE
def test_planner_parallelizes_distinct_capabilities():
 assert plan("x",("a","b"),2,TeamBudget(max_active_agents=2)).topology is TeamTopology.PARALLEL
