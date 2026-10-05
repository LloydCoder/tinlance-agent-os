from tinlance_agent_os.catalog_discovery import CatalogDiscovery, DiscoveryQuery
from tinlance_agent_os.catalog_schema import CapabilityProfile, RiskLevel
from tinlance_agent_os.catalog_store import CatalogStore


def test_discovery_filters_constraints() -> None:
    store = CatalogStore()
    store.upsert(
        CapabilityProfile(
            id="a",
            version="1",
            domain="security",
            capability_ids=("scan",),
            risk_level=RiskLevel.LOW,
            provenance=("x",),
        )
    )
    store.upsert(
        CapabilityProfile(
            id="b",
            version="1",
            domain="security",
            capability_ids=("scan",),
            risk_level=RiskLevel.HIGH,
            provenance=("x",),
        )
    )

    result = CatalogDiscovery(store).discover(
        DiscoveryQuery(capabilities=("scan",), risk_max=RiskLevel.MEDIUM)
    )
    assert [profile.id for profile in result] == ["a"]
