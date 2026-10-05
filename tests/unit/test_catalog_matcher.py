from tinlance_agent_os.catalog_matcher import MatchRequirement, match_profile
from tinlance_agent_os.catalog_schema import CapabilityProfile


def test_match_is_reproducible() -> None:
    profile = CapabilityProfile(
        id="a",
        version="1",
        domain="security",
        capability_ids=("scan", "report"),
        tools=("github",),
        provenance=("x",),
        evaluation_score=0.9,
        trust_score=0.95,
        cost_microunits=10,
        latency_ms=100,
    )
    requirement = MatchRequirement(
        frozenset(("scan",)),
        domain="security",
        tools=frozenset(("github",)),
        min_evaluation_score=0.8,
        min_trust_score=0.9,
        max_cost_microunits=20,
        max_latency_ms=200,
    )
    match = match_profile(profile, requirement)
    assert match is not None
    assert match.score == 30.0


def test_match_rejects_low_trust_profile() -> None:
    profile = CapabilityProfile(
        id="a",
        version="1",
        domain="security",
        capability_ids=("scan",),
        provenance=("x",),
        trust_score=0.2,
    )
    requirement = MatchRequirement(frozenset(("scan",)), min_trust_score=0.8)
    assert match_profile(profile, requirement) is None
