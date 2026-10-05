import pytest\nfrom tinlance_agent_os.catalog_discovery import CatalogDiscovery, DiscoveryQuery
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


def test_continuous_discovery_rejects_stale_source_updates() -> None:
    from tinlance_agent_os.catalog_discovery import (
        ContinuousDiscoveryRegistry,
        DiscoverySource,
    )

    registry = ContinuousDiscoveryRegistry({})
    registry.register(DiscoverySource("a2a", "a2a", "signed-card", 60, 100))
    assert [source.source_id for source in registry.fresh_sources(120)] == ["a2a"]
    with pytest.raises(ValueError, match="freshness"):
        registry.register(DiscoverySource("a2a", "a2a", "signed-card", 60, 99))
