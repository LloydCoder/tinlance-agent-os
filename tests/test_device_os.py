from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from tinlance_agent_os.device_os import (
    DeviceOSDesired,
    DeviceOSRuntime,
    DeviceSecurityProfile,
    OSImage,
    OSUpdate,
)
from tinlance_agent_os.store import StateStore


def make_runtime(tmp_path: Path) -> DeviceOSRuntime:
    return DeviceOSRuntime(StateStore(tmp_path / "state.db"))


def test_profiles_images_and_updates_are_durable(tmp_path: Path) -> None:
    runtime = make_runtime(tmp_path)
    runtime.register_profile(DeviceSecurityProfile("device-1", "workspace-1"))
    image = OSImage(
        "image-1",
        "44.2026.1",
        "stable",
        "a" * 64,
        "x86_64",
        "secure-boot+uki+composefs",
        "prov-1",
    )
    runtime.register_image(image)
    desired = runtime.set_desired(DeviceOSDesired("device-1", "image-1"))
    assert desired.generation == 0
    update = runtime.plan_update(
        OSUpdate("update-1", "device-1", "image-old", "image-1", "planned", "image-old")
    )
    assert runtime.set_update_state("update-1", "staged", expected_generation=0).generation == 1
    assert update.to_image_id == "image-1"


def test_image_digest_and_generation_fail_closed(tmp_path: Path) -> None:
    runtime = make_runtime(tmp_path)
    runtime.register_profile(DeviceSecurityProfile("device-1", "workspace-1"))
    with pytest.raises(ValueError, match="SHA-256"):
        runtime.register_image(OSImage("image-1", "1", "stable", "bad", "x86_64", "uki"))
    runtime.register_image(
        OSImage("image-1", "1", "stable", "b" * 64, "x86_64", "uki")
    )
    runtime.set_desired(DeviceOSDesired("device-1", "image-1"))
    with pytest.raises(ValueError, match="generation"):
        runtime.set_desired(DeviceOSDesired("device-1", "image-1"), expected_generation=1)


def test_duplicate_update_and_noop_update_fail_closed(tmp_path: Path) -> None:
    runtime = make_runtime(tmp_path)
    runtime.register_profile(DeviceSecurityProfile("device-1", "workspace-1"))
    runtime.register_image(OSImage("image-1", "1", "stable", "c" * 64, "x86_64", "uki"))
    with pytest.raises(ValueError, match="differ"):
        runtime.plan_update(OSUpdate("update-1", "device-1", "image-1", "image-1", "planned"))
    update = OSUpdate("update-1", "device-1", None, "image-1", "planned")
    runtime.plan_update(update)
    with pytest.raises(sqlite3.IntegrityError):
        runtime.plan_update(update)
