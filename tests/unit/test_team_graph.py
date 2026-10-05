from tinlance_agent_os.team_graph import TeamGraph,TeamNode
def test_graph_rejects_cycles():
 try: TeamGraph((TeamNode("a","a",("b",)),TeamNode("b","b",("a",)))).validate()
 except ValueError as e: assert "cycle" in str(e)
 else: raise AssertionError
