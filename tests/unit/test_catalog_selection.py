from tinlance_agent_os.catalog_matcher import Match
from tinlance_agent_os.catalog_schema import CapabilityProfile
from tinlance_agent_os.catalog_selection import select


def test_selection_is_deterministic() -> None:
    profile_b = CapabilityProfile(
        id="b",
        version="1",
        domain="x",
        capability_ids=("x",),
        provenance=("a",),
    )
    profile_a = CapabilityProfile(
        id="a",
        version="1",
        domain="x",
        capability_ids=("x",),
        provenance=("a",),
    )

    result = select((Match(profile_b, 10, ()), Match(profile_a, 10, ())))
    assert result is not None
    assert result.profile_id == "a"
