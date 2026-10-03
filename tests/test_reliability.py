from __future__ import annotations

import sqlite3
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from tinlance_agent_os.reliability import (
    ChaosScenario,
    DRPlan,
    ReliabilityProfile,
    ReliabilityRuntime,
    WorkerLease,
)
from tinlance_agent_os.store import StateStore


def make_runtime(tmp_path: Path) -> ReliabilityRuntime:
    return ReliabilityRuntime(StateStore(tmp_path / "state.db"))


def test_profile_dr_chaos_and_lease_lifecycle(tmp_path: Path) -> None:
    runtime = make_runtime(tmp_path)
    runtime.register_profile(
        ReliabilityProfile(
            "profile-1",
            "workspace-1",
            "postgres-distributed",
            regions=2,
            rpo_seconds=60,
            rto_seconds=300,
        )
    )
    runtime.register_dr_plan(
        DRPlan("dr-1", "workspace-1", "backup-1", "region-b", 60, 300, "tested")
    )
    runtime.register_chaos(
        ChaosScenario("chaos-1", "workspace-1", "worker-failure", "single-worker", "enabled")
    )
    lease = runtime.acquire_lease(
        WorkerLease(
            "lease-1",
            "workspace-1",
            "worker-1",
            "workflow",
            "active",
            datetime.now(UTC) + timedelta(minutes=5),
        )
    )
    released = runtime.release_lease("lease-1", expected_generation=0)
    assert lease.state == "active"
    assert released.state == "released"
    assert runtime.readiness("workspace-1") == {
        "profile_present": True,
        "distributed_ready": True,
        "targets_defined": True,
        "backup_required": True,
        "dr_tested": True,
        "chaos_enabled": True,
    }


def test_distributed_profile_requires_multiple_regions(tmp_path: Path) -> None:
    runtime = make_runtime(tmp_path)
    with pytest.raises(ValueError, match="two regions"):
        runtime.register_profile(
            ReliabilityProfile("profile-1", "workspace-1", "postgres-distributed")
        )


def test_lease_and_timestamp_safety(tmp_path: Path) -> None:
    runtime = make_runtime(tmp_path)
    with pytest.raises(ValueError, match="future"):
        runtime.acquire_lease(
            WorkerLease(
                "lease-1",
                "workspace-1",
                "worker-1",
                "workflow",
                "active",
                datetime.now(UTC) - timedelta(minutes=1),
            )
        )
    runtime.register_profile(ReliabilityProfile("profile-1", "workspace-1", "sqlite-local"))
    with pytest.raises(ValueError, match="targets"):
        runtime.register_dr_plan(DRPlan("dr-1", "workspace-1", "backup", "restore", -1, 1))


def test_duplicate_dr_and_stale_release_fail_closed(tmp_path: Path) -> None:
    runtime = make_runtime(tmp_path)
    now = datetime.now(UTC) + timedelta(minutes=5)
    runtime.acquire_lease(
        WorkerLease("lease-1", "workspace-1", "worker-1", "workflow", "active", now)
    )
    with pytest.raises(ValueError, match="active lease"):
        runtime.acquire_lease(
            WorkerLease("lease-2", "workspace-1", "worker-1", "workflow", "active", now)
        )
    with pytest.raises(ValueError, match="generation"):
        runtime.release_lease("lease-1", expected_generation=1)
    with pytest.raises(sqlite3.IntegrityError):
        runtime.register_dr_plan(
            DRPlan("dr-1", "workspace-1", "backup", "restore", 1, 1)
        )
