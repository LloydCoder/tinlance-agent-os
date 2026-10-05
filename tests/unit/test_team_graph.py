import pytest

from tinlance_agent_os.team_graph import TeamGraph, TeamNode


def test_graph_rejects_cycles() -> None:
    graph = TeamGraph(
        (
            TeamNode("a", "a", ("b",)),
            TeamNode("b", "b", ("a",)),
        )
    )
    with pytest.raises(ValueError, match="cycle"):
        graph.validate()
