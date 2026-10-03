from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from tinlance_agent_os.fleet import (
    FleetControlPlane,
    FleetDeployment,
    FleetDevice,
    FleetGroup,
)
from tinlance_agent_os.store import StateStore


def make_fleet(tmp_path: Path) -> FleetControlPlane:
    return FleetControlPlane(StateStore(tmp_path / "state.db"))


def test_fleet_registration_grouping_and_placement(tmp_path: Path) -> None:
    fleet = make_fleet(tmp_path)
    fleet.enroll_device(
        FleetDevice(
            "device-1",
            "workspace-1",
            "endpoint-1",
            "eu",
            "online",
            "1.0.0",
            10,
            2,
        )
    )
    fleet.enroll_device(
        FleetDevice(
            "device-2",
            "workspace-1",
            "endpoint-2",
            "us",
            "online",
            "1.0.0",
            10,
            9,
        )
    )
    fleet.create_group(FleetGroup("group-1", "workspace-1", "production", "eu"))
    fleet.add_device_to_group("group-1", "device-1", expected_workspace_id="workspace-1")
    fleet.add_device_to_group("group-1", "device-2", expected_workspace_id="workspace-1")
    placements = fleet.plan_placement(group_id="group-1", required_capacity=4)
    assert [item.device_id for item in placements] == ["device-1"]


def test_workspace_and_generation_boundaries_fail_closed(tmp_path: Path) -> None:
    fleet = make_fleet(tmp_path)
    fleet.enroll_device(
        FleetDevice("device-1", "workspace-1", "endpoint-1", "eu", "online", "1.0.0", 4)
    )
    fleet.create_group(FleetGroup("group-1", "workspace-2", "production"))
    with pytest.raises(ValueError, match="workspace mismatch"):
        fleet.add_device_to_group("group-1", "device-1", expected_workspace_id="workspace-1")
    with pytest.raises(ValueError, match="generation conflict"):
        fleet.update_device("device-1", expected_generation=1, state="draining")


def test_deployment_requires_matching_group_and_duplicate_ids_fail(tmp_path: Path) -> None:
    fleet = make_fleet(tmp_path)
    fleet.create_group(FleetGroup("group-1", "workspace-1", "production"))
    deployment = FleetDeployment(
        "deployment-1", "workspace-1", "group-1", "agent-1", "1.2.0", cohort=1
    )
    fleet.create_deployment(deployment)
    with pytest.raises(sqlite3.IntegrityError):
        fleet.create_deployment(deployment)
    with pytest.raises(KeyError):
        fleet.create_deployment(
            FleetDeployment("deployment-2", "workspace-2", "group-1", "agent-1", "1.2.0")
        )


def test_invalid_capacity_fails_closed(tmp_path: Path) -> None:
    fleet = make_fleet(tmp_path)
    with pytest.raises(ValueError, match="capacity"):
        fleet.enroll_device(
            FleetDevice(
                "device-1",
                "workspace-1",
                "endpoint-1",
                "eu",
                "online",
                "1.0.0",
                1,
                2,
            )
        )
