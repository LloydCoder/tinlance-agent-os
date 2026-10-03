"""Device and desktop operating-environment contracts for Agent OS.

M35 is a deployment profile for Tinlance-managed Linux devices. It models
security posture, OS images, desired deployments and recovery state without
pretending that this Python repository is itself a Linux kernel, bootloader,
TPM service or device-management agent.
"""

from __future__ import annotations

import re
import sqlite3
from dataclasses import dataclass
from typing import Final, Literal

from .store import StateStore

UpdateState = Literal["planned", "staged", "active", "failed", "rolled_back"]
Channel = Literal["stable", "canary", "lts"]

_SCHEMA: Final = """
CREATE TABLE IF NOT EXISTS device_profiles (
    device_id TEXT PRIMARY KEY,
    workspace_id TEXT NOT NULL,
    secure_boot_required INTEGER NOT NULL CHECK(secure_boot_required IN (0,1)),
    tpm_required INTEGER NOT NULL CHECK(tpm_required IN (0,1)),
    disk_encryption_required INTEGER NOT NULL CHECK(disk_encryption_required IN (0,1)),
    offline_allowed INTEGER NOT NULL CHECK(offline_allowed IN (0,1)),
    generation INTEGER NOT NULL CHECK(generation >= 0)
);

CREATE TABLE IF NOT EXISTS os_images (
    image_id TEXT PRIMARY KEY,
    version TEXT NOT NULL,
    channel TEXT NOT NULL CHECK(channel IN ('stable','canary','lts')),
    digest TEXT NOT NULL,
    architecture TEXT NOT NULL,
    boot_chain TEXT NOT NULL,
    provenance_ref TEXT,
    rollback_image_id TEXT
);

CREATE TABLE IF NOT EXISTS device_os_desired (
    device_id TEXT PRIMARY KEY REFERENCES device_profiles(device_id),
    image_id TEXT NOT NULL REFERENCES os_images(image_id),
    state TEXT NOT NULL,
    generation INTEGER NOT NULL CHECK(generation >= 0)
);

CREATE TABLE IF NOT EXISTS device_os_updates (
    update_id TEXT PRIMARY KEY,
    device_id TEXT NOT NULL REFERENCES device_profiles(device_id),
    from_image_id TEXT,
    to_image_id TEXT NOT NULL REFERENCES os_images(image_id),
    state TEXT NOT NULL,
    recovery_image_id TEXT,
    generation INTEGER NOT NULL CHECK(generation >= 0)
);
"""


@dataclass(frozen=True, slots=True)
class DeviceSecurityProfile:
    device_id: str
    workspace_id: str
    secure_boot_required: bool = True
    tpm_required: bool = True
    disk_encryption_required: bool = True
    offline_allowed: bool = False
    generation: int = 0


@dataclass(frozen=True, slots=True)
class OSImage:
    image_id: str
    version: str
    channel: Channel
    digest: str
    architecture: str
    boot_chain: str
    provenance_ref: str | None = None
    rollback_image_id: str | None = None


@dataclass(frozen=True, slots=True)
class DeviceOSDesired:
    device_id: str
    image_id: str
    state: UpdateState = "planned"
    generation: int = 0


@dataclass(frozen=True, slots=True)
class OSUpdate:
    update_id: str
    device_id: str
    from_image_id: str | None
    to_image_id: str
    state: UpdateState
    recovery_image_id: str | None = None
    generation: int = 0


class DeviceOSRuntime:
    """Durable device-OS profile, image and recovery-state contract."""

    def __init__(self, store: StateStore) -> None:
        self.store = store
        with sqlite3.connect(store.path) as db:
            db.executescript(_SCHEMA)

    @staticmethod
    def _validate_digest(digest: str) -> None:
        if not re.fullmatch(r"[0-9a-f]{64}", digest):
            raise ValueError("image digest must be a lowercase SHA-256 hex digest")

    def register_profile(self, profile: DeviceSecurityProfile) -> DeviceSecurityProfile:
        if not profile.device_id or not profile.workspace_id:
            raise ValueError("device identity is required")
        if profile.generation < 0:
            raise ValueError("generation must be non-negative")
        with sqlite3.connect(self.store.path) as db:
            db.execute(
                """INSERT INTO device_profiles
                (device_id,workspace_id,secure_boot_required,tpm_required,
                 disk_encryption_required,offline_allowed,generation)
                VALUES (?,?,?,?,?,?,?)""",
                (
                    profile.device_id,
                    profile.workspace_id,
                    int(profile.secure_boot_required),
                    int(profile.tpm_required),
                    int(profile.disk_encryption_required),
                    int(profile.offline_allowed),
                    profile.generation,
                ),
            )
        return profile

    def register_image(self, image: OSImage) -> OSImage:
        if not image.image_id or not image.version or not image.architecture:
            raise ValueError("image identity is required")
        self._validate_digest(image.digest)
        if not image.boot_chain:
            raise ValueError("boot_chain is required")
        with sqlite3.connect(self.store.path) as db:
            db.execute(
                """INSERT INTO os_images
                (image_id,version,channel,digest,architecture,boot_chain,
                 provenance_ref,rollback_image_id)
                VALUES (?,?,?,?,?,?,?,?)""",
                (
                    image.image_id,
                    image.version,
                    image.channel,
                    image.digest,
                    image.architecture,
                    image.boot_chain,
                    image.provenance_ref,
                    image.rollback_image_id,
                ),
            )
        return image

    def set_desired(
        self,
        desired: DeviceOSDesired,
        *,
        expected_generation: int | None = None,
    ) -> DeviceOSDesired:
        with sqlite3.connect(self.store.path) as db:
            profile = db.execute(
                "SELECT workspace_id FROM device_profiles WHERE device_id=?",
                (desired.device_id,),
            ).fetchone()
            image = db.execute(
                "SELECT image_id FROM os_images WHERE image_id=?", (desired.image_id,)
            ).fetchone()
            if profile is None:
                raise KeyError(f"unknown device: {desired.device_id}")
            if image is None:
                raise KeyError(f"unknown OS image: {desired.image_id}")
            current = db.execute(
                "SELECT generation FROM device_os_desired WHERE device_id=?",
                (desired.device_id,),
            ).fetchone()
            actual_generation = desired.generation if current is None else int(current[0])
            if expected_generation is not None and expected_generation != actual_generation:
                raise ValueError(
                    "generation conflict: "
                    f"expected {expected_generation}, actual {actual_generation}"
                )
            next_generation = actual_generation if current is None else actual_generation + 1
            db.execute(
                """INSERT INTO device_os_desired(device_id,image_id,state,generation)
                   VALUES (?,?,?,?)
                   ON CONFLICT(device_id) DO UPDATE SET
                     image_id=excluded.image_id,
                     state=excluded.state,
                     generation=excluded.generation""",
                (desired.device_id, desired.image_id, desired.state, next_generation),
            )
        return DeviceOSDesired(desired.device_id, desired.image_id, desired.state, next_generation)

    def plan_update(self, update: OSUpdate) -> OSUpdate:
        if not update.update_id or not update.device_id or not update.to_image_id:
            raise ValueError("update identity is required")
        if update.generation < 0:
            raise ValueError("generation must be non-negative")
        with sqlite3.connect(self.store.path) as db:
            profile = db.execute(
                "SELECT workspace_id FROM device_profiles WHERE device_id=?",
                (update.device_id,),
            ).fetchone()
            target = db.execute(
                "SELECT architecture,boot_chain FROM os_images WHERE image_id=?",
                (update.to_image_id,),
            ).fetchone()
            if profile is None:
                raise KeyError(f"unknown device: {update.device_id}")
            if target is None:
                raise KeyError(f"unknown OS image: {update.to_image_id}")
            if update.from_image_id == update.to_image_id:
                raise ValueError("source and target images must differ")
            db.execute(
                """INSERT INTO device_os_updates
                (update_id,device_id,from_image_id,to_image_id,state,recovery_image_id,generation)
                VALUES (?,?,?,?,?,?,?)""",
                (
                    update.update_id,
                    update.device_id,
                    update.from_image_id,
                    update.to_image_id,
                    update.state,
                    update.recovery_image_id,
                    update.generation,
                ),
            )
        return update

    def set_update_state(
        self,
        update_id: str,
        state: UpdateState,
        *,
        expected_generation: int,
    ) -> OSUpdate:
        with sqlite3.connect(self.store.path) as db:
            row = db.execute(
                """SELECT update_id,device_id,from_image_id,to_image_id,state,
                          recovery_image_id,generation
                   FROM device_os_updates WHERE update_id=?""",
                (update_id,),
            ).fetchone()
            if row is None:
                raise KeyError(f"unknown update: {update_id}")
            actual = int(row[6])
            if actual != expected_generation:
                raise ValueError(f"generation conflict: expected {expected_generation}, actual {actual}")
            next_generation = actual + 1
            db.execute(
                "UPDATE device_os_updates SET state=?,generation=? WHERE update_id=?",
                (state, next_generation, update_id),
            )
        return OSUpdate(
            str(row[0]),
            str(row[1]),
            row[2],
            str(row[3]),
            state,
            row[5],
            next_generation,
        )
