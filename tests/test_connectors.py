from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from tinlance_agent_os.connectors import (
    ConnectorKind,
    ConnectorManifest,
    ConnectorRegistry,
    ConnectorState,
    DataCursor,
)
from tinlance_agent_os.store import StateStore


def make_registry(tmp_path: Path) -> ConnectorRegistry:
    store = StateStore(tmp_path / "state.db")
    store.upsert_workspace("workspace-1", "user-1", "2026-10-03T00:00:00+00:00")
    return ConnectorRegistry(store)


def test_connector_registration_and_cursor_are_durable(tmp_path: Path) -> None:
    registry = make_registry(tmp_path)
    registry.register(
        ConnectorManifest(
            "connector-1",
            "workspace-1",
            "Docs API",
            ConnectorKind.HTTP_API,
            "https://example.invalid/api",
            frozenset({"read"}),
        )
    )
    registry.transition("connector-1", ConnectorState.READY)
    cursor = registry.save_cursor(
        DataCursor("connector-1", "v42", 42, datetime.now(UTC))
    )
    assert registry.get_cursor("connector-1") == cursor


def test_endpoint_and_workspace_boundaries_are_fail_closed(tmp_path: Path) -> None:
    registry = make_registry(tmp_path)
    with pytest.raises(ValueError, match="scheme"):
        registry.register(
            ConnectorManifest(
                "connector-2",
                "workspace-1",
                "Unsafe",
                ConnectorKind.HTTP_API,
                "http://example.invalid",
            )
        )
    with pytest.raises(ValueError, match="absolute"):
        registry.register(
            ConnectorManifest(
                "connector-3",
                "workspace-1",
                "Local",
                ConnectorKind.FILESYSTEM,
                "relative/path",
            )
        )
