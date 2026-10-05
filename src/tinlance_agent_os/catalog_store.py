"""Durable in-process semantic Catalog v2 storage/index primitives.

The persistence adapter is intentionally explicit: callers own durable storage
transactions; this layer supplies deterministic validation and indexes.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field

from .catalog_schema import CapabilityProfile


@dataclass(slots=True)
class CatalogIndex:
    by_capability: dict[str, set[str]] = field(default_factory=dict)
    by_domain: dict[str, set[str]] = field(default_factory=dict)
    by_tool: dict[str, set[str]] = field(default_factory=dict)
    by_environment: dict[str, set[str]] = field(default_factory=dict)
    by_protocol: dict[str, set[str]] = field(default_factory=dict)

    def add(self, profile: CapabilityProfile) -> None:
        for capability in profile.capability_ids:
            self.by_capability.setdefault(capability, set()).add(profile.id)
        self.by_domain.setdefault(profile.domain, set()).add(profile.id)
        for tool in profile.tools:
            self.by_tool.setdefault(tool, set()).add(profile.id)
        for environment in profile.environments:
            self.by_environment.setdefault(environment, set()).add(profile.id)
        for protocol in profile.protocols:
            self.by_protocol.setdefault(protocol, set()).add(profile.id)

    def remove(self, profile: CapabilityProfile) -> None:
        for mapping, values in (
            (self.by_capability, profile.capability_ids),
            (self.by_tool, profile.tools),
            (self.by_environment, profile.environments),
            (self.by_protocol, profile.protocols),
        ):
            for value in values:
                ids = mapping.get(value)
                if ids:
                    ids.discard(profile.id)
                    if not ids:
                        mapping.pop(value, None)
        ids = self.by_domain.get(profile.domain)
        if ids:
            ids.discard(profile.id)
            if not ids:
                self.by_domain.pop(profile.domain, None)


class CatalogStore:
    def __init__(self) -> None:
        self._profiles: dict[str, CapabilityProfile] = {}
        self._index = CatalogIndex()

    def upsert(self, profile: CapabilityProfile) -> None:
        old = self._profiles.get(profile.id)
        if old is not None:
            self._index.remove(old)
        self._profiles[profile.id] = profile
        self._index.add(profile)

    def get(self, profile_id: str) -> CapabilityProfile | None:
        return self._profiles.get(profile_id)

    def all(self) -> tuple[CapabilityProfile, ...]:
        return tuple(self._profiles.values())

    def ids_for_capability(self, capability: str) -> tuple[str, ...]:
        return tuple(sorted(self._index.by_capability.get(capability, ())))

    def search(
        self,
        *,
        capabilities: Iterable[str] = (),
        domain: str | None = None,
        tools: Iterable[str] = (),
        environments: Iterable[str] = (),
        protocols: Iterable[str] = (),
    ) -> tuple[CapabilityProfile, ...]:
        requested = [set(self.ids_for_capability(v)) for v in capabilities]
        candidates = set.intersection(*requested) if requested else set(self._profiles)
        if domain is not None:
            candidates &= self._index.by_domain.get(domain, set())
        for value in tools:
            candidates &= self._index.by_tool.get(value, set())
        for value in environments:
            candidates &= self._index.by_environment.get(value, set())
        for value in protocols:
            candidates &= self._index.by_protocol.get(value, set())
        return tuple(self._profiles[i] for i in sorted(candidates))


class SqliteCatalogStore(CatalogStore):
    """Durable Catalog v2 adapter with atomic SQLite upserts."""

    def __init__(self, database_path: str) -> None:
        import json
        import sqlite3

        super().__init__()
        self._database_path = database_path
        with sqlite3.connect(database_path) as db:
            db.execute(
                """
                CREATE TABLE IF NOT EXISTS agent_catalog_profiles (
                    profile_id TEXT PRIMARY KEY,
                    profile_version TEXT NOT NULL,
                    profile_json TEXT NOT NULL,
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            rows = db.execute(
                "SELECT profile_json FROM agent_catalog_profiles ORDER BY profile_id"
            ).fetchall()
        for (payload,) in rows:
            self.upsert(CapabilityProfile.from_record(json.loads(payload)))

    def upsert(self, profile: CapabilityProfile) -> None:
        import json
        import sqlite3

        super().upsert(profile)
        with sqlite3.connect(self._database_path) as db:
            db.execute(
                """
                INSERT INTO agent_catalog_profiles
                    (profile_id, profile_version, profile_json)
                VALUES (?, ?, ?)
                ON CONFLICT(profile_id) DO UPDATE SET
                    profile_version=excluded.profile_version,
                    profile_json=excluded.profile_json,
                    updated_at=CURRENT_TIMESTAMP
                """,
                (profile.id, profile.version, json.dumps(profile.to_record(), sort_keys=True)),
            )
