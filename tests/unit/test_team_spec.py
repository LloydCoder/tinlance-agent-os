from tinlance_agent_os.team_spec import TeamBudget,TeamSpec,TeamTopology
def test_team_spec_is_bounded():
 s=TeamSpec("t","goal","w","sup",("a","b"),TeamTopology.PARALLEL,TeamBudget(max_agents=2,max_active_agents=2,max_fanout=2))
 assert s.failure_policy=="fail_closed"
