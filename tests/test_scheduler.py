from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from tinlance_agent_os.scheduler import (
    JobState,
    MisfirePolicy,
    Schedule,
    ScheduleKind,
    Scheduler,
)
from tinlance_agent_os.store import StateStore


def make_scheduler(tmp_path: Path) -> Scheduler:
    return Scheduler(StateStore(tmp_path / "state.db"))


def seed_workspace(scheduler: Scheduler) -> None:
    scheduler.store.upsert_workspace("workspace-1", "user-1", "2026-10-03T00:00:00+00:00")


def test_interval_schedule_creates_one_deterministic_job(tmp_path: Path) -> None:
    scheduler = make_scheduler(tmp_path)
    seed_workspace(scheduler)
    schedule = scheduler.create(
        Schedule(
            "schedule-1",
            "workspace-1",
            "hourly",
            ScheduleKind.INTERVAL,
            "3600",
            next_run_at=datetime(2026, 10, 3, 1, tzinfo=UTC),
        )
    )

    jobs = scheduler.reconcile(now=datetime(2026, 10, 3, 1, 1, tzinfo=UTC))
    assert len(jobs) == 1
    assert jobs[0].schedule_id == schedule.schedule_id
    assert scheduler.get("schedule-1").generation == 2
    assert scheduler.reconcile(now=datetime(2026, 10, 3, 1, 1, tzinfo=UTC)) == ()


def test_skip_misfire_discards_backlog_and_reanchors_cadence(tmp_path: Path) -> None:
    scheduler = make_scheduler(tmp_path)
    seed_workspace(scheduler)
    scheduler.create(
        Schedule(
            "schedule-skip",
            "workspace-1",
            "skip",
            ScheduleKind.INTERVAL,
            "60",
            misfire_policy=MisfirePolicy.SKIP,
            next_run_at=datetime(2026, 10, 3, 0, 0, tzinfo=UTC),
        )
    )

    assert scheduler.reconcile(now=datetime(2026, 10, 3, 0, 3, tzinfo=UTC)) == ()
    assert scheduler.get("schedule-skip").next_run_at == datetime(2026, 10, 3, 0, 1, tzinfo=UTC)


def test_catch_up_preserves_each_interval_occurrence(tmp_path: Path) -> None:
    scheduler = make_scheduler(tmp_path)
    seed_workspace(scheduler)
    scheduler.create(
        Schedule(
            "schedule-2",
            "workspace-1",
            "catch-up",
            ScheduleKind.INTERVAL,
            "60",
            misfire_policy=MisfirePolicy.CATCH_UP,
            next_run_at=datetime(2026, 10, 3, 0, 0, tzinfo=UTC),
        )
    )

    jobs = scheduler.reconcile(now=datetime(2026, 10, 3, 0, 3, tzinfo=UTC))
    assert [job.scheduled_for.minute for job in jobs] == [0, 1, 2, 3]


def test_cron_weekday_mapping_uses_standard_cron_sunday_zero(tmp_path: Path) -> None:
    scheduler = make_scheduler(tmp_path)
    seed_workspace(scheduler)
    schedule = scheduler.create(
        Schedule(
            "schedule-cron",
            "workspace-1",
            "monday",
            ScheduleKind.CRON,
            "0 9 * * 1",
            timezone="UTC",
        ),
        now=datetime(2026, 10, 4, 8, 59, tzinfo=UTC),
    )
    assert schedule.next_run_at == datetime(2026, 10, 5, 9, tzinfo=UTC)


def test_cron_and_timezone_are_supported(tmp_path: Path) -> None:
    scheduler = make_scheduler(tmp_path)
    seed_workspace(scheduler)
    created = scheduler.create(
        Schedule(
            "schedule-3",
            "workspace-1",
            "daily",
            ScheduleKind.CRON,
            "0 9 * * 1-5",
            timezone="Africa/Lagos",
            next_run_at=datetime(2026, 10, 5, 8, tzinfo=UTC),
        )
    )
    assert created.next_run_at == datetime(2026, 10, 5, 8, tzinfo=UTC)


def test_max_concurrency_prevents_second_lease(tmp_path: Path) -> None:
    scheduler = make_scheduler(tmp_path)
    seed_workspace(scheduler)
    scheduler.create(
        Schedule(
            "schedule-4",
            "workspace-1",
            "one",
            ScheduleKind.ONE_SHOT,
            "2026-10-03T01:00:00+00:00",
            max_concurrency=1,
            next_run_at=datetime(2026, 10, 3, 1, tzinfo=UTC),
        )
    )
    scheduler.reconcile(now=datetime(2026, 10, 3, 1, tzinfo=UTC))
    leased = scheduler.lease_due(owner="worker-a", now=datetime(2026, 10, 3, 1, tzinfo=UTC))
    assert len(leased) == 1
    assert leased[0].state is JobState.RUNNING
    assert scheduler.lease_due(owner="worker-b", now=datetime(2026, 10, 3, 1, tzinfo=UTC)) == ()


def test_expired_lease_is_recoverable(tmp_path: Path) -> None:
    scheduler = make_scheduler(tmp_path)
    seed_workspace(scheduler)
    scheduler.create(
        Schedule(
            "schedule-5",
            "workspace-1",
            "one",
            ScheduleKind.ONE_SHOT,
            "2026-10-03T01:00:00+00:00",
            next_run_at=datetime(2026, 10, 3, 1, tzinfo=UTC),
        )
    )
    scheduler.reconcile(now=datetime(2026, 10, 3, 1, tzinfo=UTC))
    scheduler.lease_due(
        owner="worker-a",
        lease_seconds=1,
        now=datetime(2026, 10, 3, 1, tzinfo=UTC),
    )
    recovered = scheduler.lease_due(
        owner="worker-b",
        now=datetime(2026, 10, 3, 1, 0, 2, tzinfo=UTC),
    )
    assert len(recovered) == 1
    assert recovered[0].attempt == 2


def test_generation_conflict_is_rejected(tmp_path: Path) -> None:
    scheduler = make_scheduler(tmp_path)
    seed_workspace(scheduler)
    schedule = scheduler.create(
        Schedule(
            "schedule-6",
            "workspace-1",
            "one",
            ScheduleKind.ONE_SHOT,
            "2026-10-03T01:00:00+00:00",
            next_run_at=datetime(2026, 10, 3, 1, tzinfo=UTC),
        )
    )
    with pytest.raises(ValueError, match="generation conflict"):
        scheduler.update(
            schedule,
            expected_generation=99,
            now=datetime(2026, 10, 3, tzinfo=UTC),
        )


def test_dispatch_marks_failed_without_creating_authority(tmp_path: Path) -> None:
    scheduler = make_scheduler(tmp_path)
    seed_workspace(scheduler)
    scheduler.create(
        Schedule(
            "schedule-7",
            "workspace-1",
            "one",
            ScheduleKind.ONE_SHOT,
            "2026-10-03T01:00:00+00:00",
            next_run_at=datetime(2026, 10, 3, 1, tzinfo=UTC),
        )
    )
    result = scheduler.dispatch_due(
        lambda _: (_ for _ in ()).throw(RuntimeError("dispatcher failed")),
        owner="worker-a",
        now=datetime(2026, 10, 3, 1, tzinfo=UTC),
    )
    assert len(result.created_jobs) == 1
    assert result.leased_jobs[0].state is JobState.RUNNING
    job = scheduler.store.get_scheduler_job(result.leased_jobs[0].job_id)
    assert job is not None
    assert job["state"] == JobState.FAILED.value
