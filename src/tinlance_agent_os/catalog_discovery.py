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


@dataclass(frozen=True, slots=True)
class DiscoverySource:
    source_id: str
    source_type: str
    provenance: str
    ttl_seconds: int
    last_refreshed_epoch: int
    enabled: bool = True

    def is_fresh(self, now_epoch: int) -> bool:
        if not self.source_id or not self.source_type or not self.provenance:
            return False
        if self.ttl_seconds <= 0 or self.last_refreshed_epoch < 0:
            return False
        return self.enabled and now_epoch <= self.last_refreshed_epoch + self.ttl_seconds


@dataclass(slots=True)
class ContinuousDiscoveryRegistry:
    sources: dict[str, DiscoverySource]

    def register(self, source: DiscoverySource) -> None:
        if not source.source_id:
            raise ValueError("source_id is required")
        existing = self.sources.get(source.source_id)
        if existing is not None and source.last_refreshed_epoch < existing.last_refreshed_epoch:
            raise ValueError("discovery source freshness cannot move backwards")
        self.sources[source.source_id] = source

    def fresh_sources(self, now_epoch: int) -> tuple[DiscoverySource, ...]:
        return tuple(
            source
            for source in sorted(self.sources.values(), key=lambda item: item.source_id)
            if source.is_fresh(now_epoch)
        )
