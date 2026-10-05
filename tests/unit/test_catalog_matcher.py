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
    )
    requirement = MatchRequirement(
        frozenset(("scan",)),
        domain="security",
        tools=frozenset(("github",)),
    )
    match = match_profile(profile, requirement)
    assert match is not None
    assert match.score == 12.0
