from tinlance_agent_os.catalog_discovery import CatalogDiscovery,DiscoveryQuery
from tinlance_agent_os.catalog_schema import CapabilityProfile,RiskLevel
from tinlance_agent_os.catalog_store import CatalogStore
def test_discovery_filters_constraints():
 s=CatalogStore();s.upsert(CapabilityProfile(id="a",version="1",domain="security",capability_ids=("scan",),risk_level=RiskLevel.LOW,provenance=("x",)))
 s.upsert(CapabilityProfile(id="b",version="1",domain="security",capability_ids=("scan",),risk_level=RiskLevel.HIGH,provenance=("x",)))
 assert [p.id for p in CatalogDiscovery(s).discover(DiscoveryQuery(capabilities=("scan",),risk_max="medium"))]==["a"]
