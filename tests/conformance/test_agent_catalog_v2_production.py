from pathlib import Path
from tempfile import TemporaryDirectory

import pytest

from tinlance_agent_os.catalog_schema import CapabilityProfile
from tinlance_agent_os.catalog_store import SqliteCatalogStore
from tinlance_agent_os.team_graph import TeamGraph, TeamNode
from tinlance_agent_os.team_spec import TeamBudget


def profile() -> CapabilityProfile:
    return CapabilityProfile(
        id="durable",
        version="1",
        domain="engineering",
        capability_ids=("engineering.test",),
        provenance=("test",),
        trust_score=0.9,
        evaluation_score=0.9,
    )


def test_catalog_durable_write_is_recoverable() -> None:
    with TemporaryDirectory() as directory:
        path = str(Path(directory) / "catalog.db")
        store = SqliteCatalogStore(path)
        store.upsert(profile())
        reopened = SqliteCatalogStore(path)
        assert reopened.get("durable") == profile()


def test_team_graph_respects_agent_and_fanout_budget() -> None:
    graph = TeamGraph(
        (
            TeamNode("root", "root"),
            TeamNode("child-a", "a", ("root",)),
            TeamNode("child-b", "b", ("root",)),
        )
    )
    graph.validate_against_budget(TeamBudget(max_agents=3, max_active_agents=2, max_fanout=2))


def test_team_graph_rejects_excess_agents() -> None:
    graph = TeamGraph(
        (
            TeamNode("a", "a"),
            TeamNode("b", "b"),
            TeamNode("c", "c"),
        )
    )
    with pytest.raises(ValueError, match="max_agents"):
        graph.validate_against_budget(TeamBudget(max_agents=2, max_active_agents=2))


def test_team_graph_rejects_excess_depth() -> None:
    graph = TeamGraph(
        (
            TeamNode("a", "a"),
            TeamNode("b", "b", ("a",)),
            TeamNode("c", "c", ("b",)),
        )
    )
    with pytest.raises(ValueError, match="max_depth"):
        graph.validate_against_budget(TeamBudget(max_agents=3, max_active_agents=2, max_depth=1))
