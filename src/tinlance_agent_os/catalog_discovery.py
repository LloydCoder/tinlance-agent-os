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
    min_evaluation_score: float = 0.0
    min_trust_score: float = 0.0
    max_cost_microunits: int | None = None
    max_latency_ms: int | None = None


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
        profiles = tuple(
            profile
            for profile in profiles
            if profile.evaluation_score >= query.min_evaluation_score
            and profile.trust_score >= query.min_trust_score
            and (
                query.max_cost_microunits is None
                or profile.cost_microunits <= query.max_cost_microunits
            )
            and (query.max_latency_ms is None or profile.latency_ms <= query.max_latency_ms)
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
        return tuple(profile for profile in profiles if rank[profile.risk_level] <= limit)
