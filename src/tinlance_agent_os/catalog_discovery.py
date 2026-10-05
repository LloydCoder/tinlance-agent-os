"""Deterministic, authority-neutral Catalog discovery."""

from __future__ import annotations

from dataclasses import dataclass

from .catalog_schema import CapabilityProfile, RiskLevel
from .catalog_store import CatalogStore


@dataclass(frozen=True, slots=True)
class DiscoveryQuery:
    capabilities: tuple[str, ...] = ()
    domain: str | None = None
    tools: tuple[str, ...] = ()
    environments: tuple[str, ...] = ()
    protocols: tuple[str, ...] = ()
    risk_max: RiskLevel | None = None


class CatalogDiscovery:
    def __init__(self, store: CatalogStore) -> None:
        self.store = store

    def discover(self, query: DiscoveryQuery) -> tuple[CapabilityProfile, ...]:
        profiles = self.store.search(
            capabilities=query.capabilities,
            domain=query.domain,
            tools=query.tools,
            environments=query.environments,
            protocols=query.protocols,
        )
        if query.risk_max is None:
            return profiles
        rank = {
            RiskLevel.LOW: 0,
            RiskLevel.MEDIUM: 1,
            RiskLevel.HIGH: 2,
            RiskLevel.CRITICAL: 3,
        }
        limit = rank[query.risk_max]
        return tuple(
            profile
            for profile in profiles
            if rank[profile.risk_level] <= limit
        )
