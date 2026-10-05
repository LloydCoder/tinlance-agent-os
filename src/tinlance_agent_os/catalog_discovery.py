"""Deterministic, authority-neutral Catalog discovery."""
from __future__ import annotations
from dataclasses import dataclass
from .catalog_schema import CapabilityProfile
from .catalog_store import CatalogStore

@dataclass(frozen=True, slots=True)
class DiscoveryQuery:
    capabilities: tuple[str,...]=()
    domain: str|None=None
    tools: tuple[str,...]=()
    environments: tuple[str,...]=()
    protocols: tuple[str,...]=()
    risk_max: str|None=None

class CatalogDiscovery:
    def __init__(self, store: CatalogStore) -> None: self.store=store
    def discover(self, query: DiscoveryQuery) -> tuple[CapabilityProfile,...]:
        profiles=self.store.search(capabilities=query.capabilities,domain=query.domain,tools=query.tools,environments=query.environments,protocols=query.protocols)
        if query.risk_max is None: return profiles
        rank={"low":0,"medium":1,"high":2,"critical":3}
        limit=rank[query.risk_max]
        return tuple(p for p in profiles if rank[p.risk_level.value] <= limit)
