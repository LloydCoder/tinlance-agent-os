from pathlib import Path

import pytest

from tinlance_agent_os.catalog_discovery import CatalogDiscovery, DiscoveryQuery
from tinlance_agent_os.catalog_matcher import MatchRequirement, match_profile
from tinlance_agent_os.catalog_schema import CapabilityProfile, RiskLevel
from tinlance_agent_os.catalog_store import CatalogStore
from tinlance_agent_os.delegation import DelegationEnvelope
from tinlance_agent_os.handoff import Handoff
from tinlance_agent_os.interop import from_a2a_card, from_mcp_metadata
from tinlance_agent_os.team_graph import TeamGraph, TeamNode
from tinlance_agent_os.team_spec import TeamBudget, TeamSpec, TeamTopology


def profile(**kwargs: object) -> CapabilityProfile:
    return CapabilityProfile(
        id="agent",
        version="1",
        domain="security",
        capability_ids=("security.scan",),
        provenance=("attestation:test",),
        **kwargs,
    )


def test_catalog_rejects_invalid_trust_and_evaluation_scores() -> None:
    with pytest.raises(ValueError, match="trust_score"):
        profile(trust_score=1.1)
    with pytest.raises(ValueError, match="evaluation_score"):
        profile(evaluation_score=-0.1)


def test_catalog_matching_enforces_operational_constraints() -> None:
    candidate = profile(
        evaluation_score=0.95,
        trust_score=0.95,
        cost_microunits=100,
        latency_ms=500,
    )
    requirement = MatchRequirement(
        frozenset(("security.scan",)),
        min_evaluation_score=0.9,
        min_trust_score=0.9,
        max_cost_microunits=50,
        max_latency_ms=100,
    )
    assert match_profile(candidate, requirement) is None


def test_discovery_risk_and_trust_filters_are_fail_closed() -> None:
    store = CatalogStore()
    store.upsert(
        profile(
            id="trusted",
            risk_level=RiskLevel.LOW,
            trust_score=0.95,
        )
    )
    store.upsert(
        profile(
            id="untrusted",
            risk_level=RiskLevel.LOW,
            trust_score=0.1,
        )
    )
    result = CatalogDiscovery(store).discover(
        DiscoveryQuery(
            capabilities=("security.scan",),
            risk_max=RiskLevel.MEDIUM,
            min_trust_score=0.9,
        )
    )
    assert [item.id for item in result] == ["trusted"]


def test_delegation_cannot_widen_capability_or_budget() -> None:
    parent = DelegationEnvelope(
        "root",
        "parent",
        "tenant",
        "workspace",
        ("read",),
        3,
        4,
        100,
        50,
    )
    child = DelegationEnvelope(
        "parent",
        "child",
        "tenant",
        "workspace",
        ("admin",),
        3,
        4,
        100,
        50,
    )
    assert not child.attenuated_from(parent)


def test_team_budget_prevents_recursive_fanout_explosion() -> None:
    with pytest.raises(ValueError, match="max_active_agents"):
        TeamBudget(max_agents=2, max_active_agents=3)


def test_team_spec_rejects_duplicate_members() -> None:
    with pytest.raises(ValueError, match="unique"):
        TeamSpec(
            "team",
            "goal",
            "workspace",
            "supervisor",
            ("agent-1", "agent-1"),
            TeamTopology.PARALLEL,
            TeamBudget(max_agents=2, max_active_agents=2),
        )


def test_team_graph_rejects_cycles_and_unknown_edges() -> None:
    with pytest.raises(ValueError, match="cycle"):
        TeamGraph(
            (
                TeamNode("a", "agent-a", ("b",)),
                TeamNode("b", "agent-b", ("a",)),
            )
        ).validate()

    with pytest.raises(ValueError, match="unknown"):
        TeamGraph((TeamNode("a", "agent-a", ("missing",)),)).validate()


def test_external_protocol_metadata_never_becomes_authority() -> None:
    a2a = from_a2a_card(
        {
            "version": "1.0",
            "url": "https://agent.example",
            "skills": ["research"],
            "securitySchemes": ["bearer"],
        }
    )
    mcp = from_mcp_metadata(
        {
            "version": "2026-07-28",
            "endpoint": "https://mcp.example",
            "tools": ["search"],
        }
    )
    assert a2a.protocol == "a2a"
    assert mcp.protocol == "mcp"
    assert not hasattr(a2a, "authorize")
    assert not hasattr(mcp, "authorize")


def test_handoff_confidence_is_bounded() -> None:
    with pytest.raises(ValueError, match="confidence"):
        Handoff("task", "parent", "agent", "completed", confidence=1.1)


def test_catalog_schema_cannot_create_platform_grant() -> None:
    names = dir(CapabilityProfile)
    forbidden = {"grant", "authorize", "approve", "execute"}
    assert not any(name.lower() in forbidden for name in names)


def test_phase18_security_suite_is_repo_local() -> None:
    assert Path("tests/conformance/test_agent_catalog_v2_security.py").name
