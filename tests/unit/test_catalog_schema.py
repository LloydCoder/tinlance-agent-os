from tinlance_agent_os.catalog_schema import AutonomyLevel, CapabilityProfile, RiskLevel


def test_profile_serialization_and_invariants() -> None:
    p = CapabilityProfile(
        id="agent.security",
        version="1.0.0",
        domain="security",
        capability_ids=("security.review",),
        risk_level=RiskLevel.HIGH,
        autonomy_level=AutonomyLevel.BOUNDED,
        delegation_allowed=True,
        max_delegation_depth=2,
        max_fanout=4,
        provenance=("m36:package@1.2.3",),
    )
    record = p.to_record()
    assert record["schema"] == "tinlance.agent-profile.v2"
    assert record["capabilities"] == ["security.review"]
    assert record["max_fanout"] == 4

def test_profile_rejects_undeclared_delegation_limits() -> None:
    try:
        CapabilityProfile(
            id="x",
            version="1",
            domain="x",
            capability_ids=("x",),
            max_fanout=1,
            provenance=("test",),
        )
    except ValueError as exc:
        assert "delegation_allowed" in str(exc)
    else:
        raise AssertionError("invalid delegation limits must fail")
