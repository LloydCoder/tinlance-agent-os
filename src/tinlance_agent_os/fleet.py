"""Enterprise fleet and remote control-plane lifecycle contracts.

M34 models device/endpoint inventory, fleet grouping, deployment desired state,
health and rollout planning. It is an OS control-plane seam: authorization,
identity, approvals and consequential execution remain in Agent Platform.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from typing import Final, Literal

from .store import StateStore

DeviceState = Literal["enrolled", "online", "draining", "offline", "quarantined"]
DeploymentState = Literal["planned", "queued", "deploying", "active", "failed", "rolled_back"]

_SCHEMA: Final = """
CREATE TABLE IF NOT EXISTS fleet_devices (
    device_id TEXT PRIMARY KEY,
    workspace_id TEXT NOT NULL,
    endpoint_id TEXT NOT NULL UNIQUE,
    region TEXT NOT NULL,
    state TEXT NOT NULL,
    platform_version TEXT NOT NULL,
    capacity INTEGER NOT NULL CHECK(capacity >= 0),
    used_capacity INTEGER NOT NULL CHECK(used_capacity >= 0),
    capabilities TEXT NOT NULL,
    attestation_ref TEXT,
    generation INTEGER NOT NULL CHECK(generation >= 0)
);
CREATE INDEX IF NOT EXISTS idx_fleet_devices_region_state
    ON fleet_devices(region, state);

CREATE TABLE IF NOT EXISTS fleet_groups (
    group_id TEXT PRIMARY KEY,
    workspace_id TEXT NOT NULL,
    name TEXT NOT NULL,
    region TEXT,
    generation INTEGER NOT NULL CHECK(generation >= 0)
);

CREATE TABLE IF NOT EXISTS fleet_group_members (
    group_id TEXT NOT NULL REFERENCES fleet_groups(group_id),
    device_id TEXT NOT NULL REFERENCES fleet_devices(device_id),
    PRIMARY KEY(group_id, device_id)
);

CREATE TABLE IF NOT EXISTS fleet_deployments (
    deployment_id TEXT PRIMARY KEY,
    workspace_id TEXT NOT NULL,
    group_id TEXT NOT NULL REFERENCES fleet_groups(group_id),
    agent_id TEXT NOT NULL,
    version TEXT NOT NULL,
    cohort INTEGER NOT NULL CHECK(cohort >= 0),
    state TEXT NOT NULL,
    generation INTEGER NOT NULL CHECK(generation >= 0)
);
CREATE INDEX IF NOT EXISTS idx_fleet_deployments_group
    ON fleet_deployments(group_id, state);
"""


@dataclass(frozen=True, slots=True)
class FleetDevice:
    device_id: str
    workspace_id: str
    endpoint_id: str
    region: str
    state: DeviceState
    platform_version: str
    capacity: int
    used_capacity: int = 0
    capabilities: str = ""
    attestation_ref: str | None = None
    generation: int = 0


@dataclass(frozen=True, slots=True)
class FleetGroup:
    group_id: str
    workspace_id: str
    name: str
    region: str | None = None
    generation: int = 0


@dataclass(frozen=True, slots=True)
class FleetDeployment:
    deployment_id: str
    workspace_id: str
    group_id: str
    agent_id: str
    version: str
    cohort: int = 0
    state: DeploymentState = "planned"
    generation: int = 0


@dataclass(frozen=True, slots=True)
class Placement:
    device_id: str
    region: str
    available_capacity: int


class FleetControlPlane:
    """Durable fleet desired-state and placement planning surface."""

    def __init__(self, store: StateStore) -> None:
        self.store = store
        with sqlite3.connect(store.path) as db:
            db.executescript(_SCHEMA)

    @staticmethod
    def _require_generation(expected: int, actual: int) -> None:
        if expected != actual:
            raise ValueError(f"generation conflict: expected {expected}, actual {actual}")

    def enroll_device(self, device: FleetDevice) -> FleetDevice:
        if not device.device_id or not device.workspace_id or not device.endpoint_id:
            raise ValueError("device identity is required")
        if not device.region or not device.platform_version:
            raise ValueError("device region and platform_version are required")
        if device.capacity < 0 or device.used_capacity < 0:
            raise ValueError("device capacity must be non-negative")
        if device.used_capacity > device.capacity:
            raise ValueError("used_capacity cannot exceed capacity")
        if device.generation < 0:
            raise ValueError("generation must be non-negative")
        with sqlite3.connect(self.store.path) as db:
            db.execute(
                """INSERT INTO fleet_devices
                (device_id,workspace_id,endpoint_id,region,state,platform_version,
                 capacity,used_capacity,capabilities,attestation_ref,generation)
                VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    device.device_id,
                    device.workspace_id,
                    device.endpoint_id,
                    device.region,
                    device.state,
                    device.platform_version,
                    device.capacity,
                    device.used_capacity,
                    device.capabilities,
                    device.attestation_ref,
                    device.generation,
                ),
            )
        return device

    def update_device(
        self,
        device_id: str,
        *,
        expected_generation: int,
        state: DeviceState | None = None,
        platform_version: str | None = None,
        capacity: int | None = None,
        used_capacity: int | None = None,
        attestation_ref: str | None = None,
    ) -> FleetDevice:
        with sqlite3.connect(self.store.path) as db:
            row = db.execute(
                """SELECT device_id,workspace_id,endpoint_id,region,state,platform_version,
                          capacity,used_capacity,capabilities,attestation_ref,generation
                   FROM fleet_devices WHERE device_id=?""",
                (device_id,),
            ).fetchone()
            if row is None:
                raise KeyError(f"unknown device: {device_id}")
            self._require_generation(expected_generation, int(row[10]))
            next_capacity = int(row[6]) if capacity is None else capacity
            next_used = int(row[7]) if used_capacity is None else used_capacity
            if next_capacity < 0 or next_used < 0 or next_used > next_capacity:
                raise ValueError("invalid device capacity")
            next_generation = int(row[10]) + 1
            db.execute(
                """UPDATE fleet_devices
                   SET state=?,platform_version=?,capacity=?,used_capacity=?,
                       attestation_ref=?,generation=?
                   WHERE device_id=?""",
                (
                    state or str(row[4]),
                    platform_version or str(row[5]),
                    next_capacity,
                    next_used,
                    attestation_ref if attestation_ref is not None else row[9],
                    next_generation,
                    device_id,
                ),
            )
            return FleetDevice(
                str(row[0]),
                str(row[1]),
                str(row[2]),
                str(row[3]),
                state or str(row[4]),
                platform_version or str(row[5]),
                next_capacity,
                next_used,
                str(row[8]),
                attestation_ref if attestation_ref is not None else row[9],
                next_generation,
            )

    def create_group(self, group: FleetGroup) -> FleetGroup:
        if not group.group_id or not group.workspace_id or not group.name:
            raise ValueError("group identity is required")
        if group.generation < 0:
            raise ValueError("generation must be non-negative")
        with sqlite3.connect(self.store.path) as db:
            db.execute(
                """INSERT INTO fleet_groups
                (group_id,workspace_id,name,region,generation)
                VALUES (?,?,?,?,?)""",
                (
                    group.group_id,
                    group.workspace_id,
                    group.name,
                    group.region,
                    group.generation,
                ),
            )
        return group

    def add_device_to_group(
        self, group_id: str, device_id: str, *, expected_workspace_id: str
    ) -> None:
        with sqlite3.connect(self.store.path) as db:
            group = db.execute(
                "SELECT workspace_id FROM fleet_groups WHERE group_id=?", (group_id,)
            ).fetchone()
            device = db.execute(
                "SELECT workspace_id FROM fleet_devices WHERE device_id=?", (device_id,)
            ).fetchone()
            if group is None or device is None:
                raise KeyError("unknown fleet group or device")
            if str(group[0]) != expected_workspace_id or str(device[0]) != expected_workspace_id:
                raise ValueError("workspace mismatch")
            db.execute(
                "INSERT INTO fleet_group_members(group_id,device_id) VALUES (?,?)",
                (group_id, device_id),
            )

    def create_deployment(self, deployment: FleetDeployment) -> FleetDeployment:
        if not deployment.deployment_id or not deployment.workspace_id:
            raise ValueError("deployment identity is required")
        if not deployment.group_id or not deployment.agent_id or not deployment.version:
            raise ValueError("deployment target is required")
        if deployment.cohort < 0 or deployment.generation < 0:
            raise ValueError("cohort and generation must be non-negative")
        with sqlite3.connect(self.store.path) as db:
            group = db.execute(
                "SELECT workspace_id FROM fleet_groups WHERE group_id=?",
                (deployment.group_id,),
            ).fetchone()
            if group is None:
                raise KeyError(f"unknown fleet group: {deployment.group_id}")
            if str(group[0]) != deployment.workspace_id:
                raise ValueError("deployment workspace does not match group")
            db.execute(
                """INSERT INTO fleet_deployments
                (deployment_id,workspace_id,group_id,agent_id,version,cohort,state,generation)
                VALUES (?,?,?,?,?,?,?,?)""",
                (
                    deployment.deployment_id,
                    deployment.workspace_id,
                    deployment.group_id,
                    deployment.agent_id,
                    deployment.version,
                    deployment.cohort,
                    deployment.state,
                    deployment.generation,
                ),
            )
        return deployment

    def plan_placement(
        self,
        *,
        group_id: str,
        required_capacity: int = 1,
        region: str | None = None,
    ) -> list[Placement]:
        if required_capacity < 0:
            raise ValueError("required_capacity must be non-negative")
        with sqlite3.connect(self.store.path) as db:
            row = db.execute(
                "SELECT workspace_id,region FROM fleet_groups WHERE group_id=?", (group_id,)
            ).fetchone()
            if row is None:
                raise KeyError(f"unknown fleet group: {group_id}")
            group_workspace, group_region = str(row[0]), row[1]
            target_region = region or (str(group_region) if group_region else None)
            query = """SELECT d.device_id,d.region,d.capacity,d.used_capacity
                       FROM fleet_devices d
                       JOIN fleet_group_members m ON m.device_id=d.device_id
                       WHERE m.group_id=? AND d.workspace_id=?
                         AND d.state IN ('enrolled','online')"""
            params: list[object] = [group_id, group_workspace]
            if target_region is not None:
                query += " AND d.region=?"
                params.append(target_region)
            query += " ORDER BY (d.capacity-d.used_capacity) DESC, d.device_id"
            rows = db.execute(query, params).fetchall()
        return [
            Placement(str(row[0]), str(row[1]), int(row[2]) - int(row[3]))
            for row in rows
            if int(row[2]) - int(row[3]) >= required_capacity
        ]
