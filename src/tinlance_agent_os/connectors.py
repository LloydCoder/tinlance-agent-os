"""Connector and data-space lifecycle contracts.

Connectors own data-source lifecycle and synchronization metadata. They do not
become an authorization or tool-execution authority; consequential operations
still cross the Agent Platform boundary.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from urllib.parse import urlparse

from .store import StateStore


class ConnectorKind(StrEnum):
    FILESYSTEM = "filesystem"
    GIT = "git"
    DATABASE = "database"
    OBJECT_STORAGE = "object_storage"
    HTTP_API = "http_api"
    SAAS = "saas"
    MESSAGING = "messaging"
    KNOWLEDGE = "knowledge"
    MCP = "mcp"


class ConnectorState(StrEnum):
    REGISTERED = "registered"
    READY = "ready"
    DEGRADED = "degraded"
    DISABLED = "disabled"
    QUARANTINED = "quarantined"


@dataclass(frozen=True, slots=True)
class ConnectorManifest:
    connector_id: str
    workspace_id: str
    name: str
    kind: ConnectorKind
    endpoint: str
    capabilities: frozenset[str] = frozenset()
    metadata: dict[str, object] | None = None


@dataclass(frozen=True, slots=True)
class DataCursor:
    connector_id: str
    cursor: str
    version: int
    observed_at: datetime


class ConnectorRegistry:
    def __init__(self, store: StateStore) -> None:
        self.store = store

    def register(self, manifest: ConnectorManifest, *, now: datetime | None = None) -> None:
        self._validate_endpoint(manifest.kind, manifest.endpoint)
        current = self._now(now)
        self.store.put_connector(
            (
                manifest.connector_id,
                manifest.workspace_id,
                manifest.name,
                manifest.kind.value,
                manifest.endpoint,
                ConnectorState.REGISTERED.value,
                json.dumps(sorted(manifest.capabilities)),
                json.dumps(manifest.metadata or {}, sort_keys=True),
                current.isoformat(),
                current.isoformat(),
            )
        )

    def transition(
        self,
        connector_id: str,
        state: ConnectorState,
        *,
        now: datetime | None = None,
    ) -> None:
        current = self._now(now)
        if self.store.get_connector(connector_id) is None:
            raise KeyError(connector_id)
        self.store.update_connector_state(connector_id, state.value, current.isoformat())

    def save_cursor(self, cursor: DataCursor) -> DataCursor:
        row = self.store.get_connector(cursor.connector_id)
        if row is None:
            raise KeyError(cursor.connector_id)
        if cursor.version < 1:
            raise ValueError("cursor version must be positive")
        self.store.put_connector_cursor(
            (
                cursor.connector_id,
                cursor.cursor,
                cursor.version,
                cursor.observed_at.astimezone(UTC).isoformat(),
            )
        )
        return cursor

    def get_cursor(self, connector_id: str) -> DataCursor | None:
        row = self.store.get_connector_cursor(connector_id)
        if row is None:
            return None
        return DataCursor(
            connector_id,
            str(row["cursor"]),
            int(row["version"]),
            datetime.fromisoformat(str(row["observed_at"])),
        )

    @staticmethod
    def _validate_endpoint(kind: ConnectorKind, endpoint: str) -> None:
        if kind is ConnectorKind.FILESYSTEM:
            if not endpoint.startswith("/"):
                raise ValueError("filesystem connector must use an absolute path")
            return
        parsed = urlparse(endpoint)
        if parsed.scheme not in {"https", "git", "s3", "mcp"}:
            raise ValueError("connector endpoint scheme is not allowed")
        if "\\n" in endpoint or "\\r" in endpoint:
            raise ValueError("connector endpoint contains control characters")

    @staticmethod
    def _now(value: datetime | None) -> datetime:
        current = value or datetime.now(UTC)
        if current.tzinfo is None:
            raise ValueError("connector time must be timezone-aware")
        return current.astimezone(UTC)
