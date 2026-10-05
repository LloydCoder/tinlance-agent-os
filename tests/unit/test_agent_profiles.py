from tinlance_agent_os.agent_profiles import (
    AgentCapabilityBinding,
    AgentProfileCatalog,
)
from tinlance_agent_os.catalog_schema import CapabilityProfile
from tinlance_agent_os.catalog_store import CatalogStore


def test_reference_agent_binding_is_versioned() -> None:
    store = CatalogStore()
    catalog = AgentProfileCatalog(store)
    profile = CapabilityProfile(
        id="research",
        version="1",
        domain="research",
        capability_ids=("research.web",),
        provenance=("m36:pkg",),
    )
    catalog.bind(
        AgentCapabilityBinding(
            "agent-1",
            "research",
            "m26:agent-1",
            "m36:pkg@1",
            "1",
        ),
        profile,
    )
    assert catalog.profile_for("agent-1") == profile
