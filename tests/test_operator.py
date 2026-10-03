from __future__ import annotations

import sqlite3
from datetime import UTC, datetime
from pathlib import Path

import pytest

from tinlance_agent_os.operator import OperatorCommand, OperatorEntity, OperatorPlane
from tinlance_agent_os.store import StateStore


def make_plane(tmp_path: Path) -> OperatorPlane:
    return OperatorPlane(StateStore(tmp_path / "state.db"))


def test_operator_projection_is_durable_and_workspace_scoped(tmp_path: Path) -> None:
    plane = make_plane(tmp_path)
    plane.upsert_entity(
        OperatorEntity(
            "agent",
            "agent-1",
            "workspace-1",
            "running",
            "healthy",
            "1.0.0",
            "Research agent",
            datetime(2026, 10, 3, tzinfo=UTC),
        )
    )
    plane.upsert_entity(
        OperatorEntity("workflow", "workflow-1", "workspace-1", "queued", "healthy")
    )
    assert [item.entity_id for item in plane.list_entities("workspace-1")] == [
        "agent-1",
        "workflow-1",
    ]
    assert plane.list_entities("workspace-2") == []


def test_projection_generation_and_filters_are_deterministic(tmp_path: Path) -> None:
    plane = make_plane(tmp_path)
    first = plane.upsert_entity(
        OperatorEntity("agent", "agent-1", "workspace-1", "running", "healthy")
    )
    second = plane.upsert_entity(
        OperatorEntity("agent", "agent-1", "workspace-1", "paused", "degraded")
    )
    assert first.generation == 0
    assert second.generation == 1
    assert [item.status for item in plane.list_entities("workspace-1", status="paused")] == [
        "paused"
    ]


def test_operator_commands_are_intents_not_execution_and_are_unique(tmp_path: Path) -> None:
    plane = make_plane(tmp_path)
    command = OperatorCommand(
        "command-1",
        "workspace-1",
        "agent",
        "agent-1",
        "restart",
        "sha256:params",
    )
    plane.request_command(command)
    with pytest.raises(sqlite3.IntegrityError):
        plane.request_command(command)
    with pytest.raises(ValueError, match="timestamp"):
        plane.request_command(
            OperatorCommand(
                "command-2",
                "workspace-1",
                "agent",
                "agent-1",
                "restart",
                "sha256:params",
                created_at=datetime(2026, 10, 3),
            )
        )
