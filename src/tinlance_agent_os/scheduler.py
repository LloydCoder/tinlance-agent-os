"""Durable scheduler and job runtime for Agent OS.

The scheduler owns temporal lifecycle and job leasing. It never grants authority or
executes consequential actions; dispatched jobs must enter the existing Task/Workflow
runtime and Agent Platform governed execution path.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from enum import StrEnum
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from .store import StateStore


class ScheduleKind(StrEnum):
    CRON = "cron"
    INTERVAL = "interval"
    ONE_SHOT = "one_shot"
    CALENDAR = "calendar"


class MisfirePolicy(StrEnum):
    SKIP = "skip"
    RUN_ONCE = "run_once"
    CATCH_UP = "catch_up"


class JobState(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"
    DEAD_LETTER = "dead_letter"


@dataclass(frozen=True, slots=True)
class Schedule:
    schedule_id: str
    workspace_id: str
    name: str
    kind: ScheduleKind
    expression: str
    timezone: str = "UTC"
    enabled: bool = True
    misfire_policy: MisfirePolicy = MisfirePolicy.RUN_ONCE
    max_concurrency: int = 1
    next_run_at: datetime | None = None
    generation: int = 1
    metadata: Mapping[str, object] = None  # type: ignore[assignment]

    def __post_init__(self) -> None:
        if not self.schedule_id or not self.workspace_id or not self.name:
            raise ValueError("schedule_id, workspace_id and name are required")
        if self.max_concurrency < 1:
            raise ValueError("max_concurrency must be at least 1")
        try:
            ZoneInfo(self.timezone)
        except ZoneInfoNotFoundError as exc:
            raise ValueError("unknown scheduler timezone") from exc
        if self.generation < 1:
            raise ValueError("generation must be positive")
        if self.next_run_at is not None and self.next_run_at.tzinfo is None:
            raise ValueError("next_run_at must be timezone-aware")


@dataclass(frozen=True, slots=True)
class Job:
    job_id: str
    schedule_id: str
    workspace_id: str
    scheduled_for: datetime
    state: JobState
    attempt: int
    payload: Mapping[str, object]
    error: str | None = None


@dataclass(frozen=True, slots=True)
class SchedulerRun:
    created_jobs: tuple[Job, ...]
    leased_jobs: tuple[Job, ...]


class CronExpression:
    """Small deterministic five-field cron parser.

    Fields are minute, hour, day-of-month, month and day-of-week. Lists, ranges,
    '*' and step expressions are supported. Day-of-month/day-of-week follows
    standard cron OR semantics when both fields are restricted.
    """

    def __init__(self, expression: str) -> None:
        fields = expression.split()
        if len(fields) != 5:
            raise ValueError("cron expression must contain five fields")
        self._minute = self._field(fields[0], 0, 59)
        self._hour = self._field(fields[1], 0, 23)
        self._day = self._field(fields[2], 1, 31)
        self._month = self._field(fields[3], 1, 12)
        self._weekday = self._field(fields[4], 0, 6)
        self._day_restricted = fields[2] != "*"
        self._weekday_restricted = fields[4] != "*"

    @staticmethod
    def _field(value: str, minimum: int, maximum: int) -> frozenset[int]:
        result: set[int] = set()
        for part in value.split(","):
            base, _, step_text = part.partition("/")
            step = int(step_text) if step_text else 1
            if step < 1:
                raise ValueError("cron step must be positive")
            if base == "*":
                start, stop = minimum, maximum
            elif "-" in base:
                start_text, stop_text = base.split("-", 1)
                start, stop = int(start_text), int(stop_text)
            else:
                start = stop = int(base)
            if start < minimum or stop > maximum or start > stop:
                raise ValueError("cron field value out of range")
            result.update(range(start, stop + 1, step))
        if not result:
            raise ValueError("cron field cannot be empty")
        return frozenset(result)

    def matches(self, value: datetime) -> bool:
        if value.minute not in self._minute or value.hour not in self._hour:
            return False
        if value.month not in self._month:
            return False
        dom = value.day in self._day
        dow = value.weekday() in self._weekday
        if self._day_restricted and self._weekday_restricted:
            day_match = dom or dow
        elif self._day_restricted:
            day_match = dom
        elif self._weekday_restricted:
            day_match = dow
        else:
            day_match = True
        return day_match

    def next_after(self, value: datetime) -> datetime:
        candidate = value.astimezone(value.tzinfo).replace(second=0, microsecond=0) + timedelta(minutes=1)
        limit = candidate + timedelta(days=366 * 2)
        while candidate <= limit:
            if self.matches(candidate):
                return candidate
            candidate += timedelta(minutes=1)
        raise ValueError("cron expression has no occurrence within two years")


class Scheduler:
    """Durable scheduler with generation-safe updates and leased jobs."""

    def __init__(self, store: StateStore) -> None:
        self.store = store

    def create(self, schedule: Schedule, *, now: datetime | None = None) -> Schedule:
        current = self._now(now)
        next_run = schedule.next_run_at or self._first_occurrence(schedule, current)
        normalized = self._with_next(schedule, next_run.astimezone(UTC))
        self.store.put_scheduler_schedule(
            (
                normalized.schedule_id,
                normalized.workspace_id,
                normalized.name,
                normalized.kind.value,
                normalized.expression,
                normalized.timezone,
                int(normalized.enabled),
                normalized.misfire_policy.value,
                normalized.max_concurrency,
                normalized.next_run_at.isoformat() if normalized.next_run_at else "",
                None,
                normalized.generation,
                json.dumps(dict(normalized.metadata or {}), sort_keys=True),
                current.isoformat(),
                current.isoformat(),
            )
        )
        return normalized

    def get(self, schedule_id: str) -> Schedule:
        row = self.store.get_scheduler_schedule(schedule_id)
        if row is None:
            raise KeyError(schedule_id)
        return self._schedule_from_row(row)

    def update(
        self,
        schedule: Schedule,
        *,
        expected_generation: int,
        now: datetime | None = None,
    ) -> Schedule:
        current = self._now(now)
        next_run = schedule.next_run_at or self._first_occurrence(schedule, current)
        updated = self._with_next(
            schedule, next_run.astimezone(UTC), generation=expected_generation + 1
        )
        self.store.update_scheduler_schedule(
            schedule.schedule_id,
            expected_generation=expected_generation,
            enabled=updated.enabled,
            next_run_at=updated.next_run_at.isoformat() if updated.next_run_at else "",
            last_run_at=None,
            generation=updated.generation,
            expression=updated.expression,
            timezone=updated.timezone,
            misfire_policy=updated.misfire_policy.value,
            max_concurrency=updated.max_concurrency,
            metadata=json.dumps(dict(updated.metadata or {}), sort_keys=True),
            updated_at=current.isoformat(),
        )
        return updated

    def reconcile(self, *, now: datetime | None = None, limit: int = 100) -> tuple[Job, ...]:
        current = self._now(now)
        rows = self.store.due_scheduler_schedules(current.isoformat())[:limit]
        created: list[Job] = []
        for row in rows:
            schedule = self._schedule_from_row(row)
            occurrences = self._due_occurrences(schedule, current)
            if schedule.misfire_policy is MisfirePolicy.SKIP:
                occurrences = (current.astimezone(UTC),)
            elif schedule.misfire_policy is MisfirePolicy.RUN_ONCE:
                occurrences = (occurrences[-1] if occurrences else current.astimezone(UTC),)
            for occurrence in occurrences:
                job_id = hashlib.sha256(
                    f"{schedule.schedule_id}:{occurrence.isoformat()}".encode()
                ).hexdigest()
                if self.store.create_scheduler_job(
                    job_id=job_id,
                    schedule_id=schedule.schedule_id,
                    workspace_id=schedule.workspace_id,
                    scheduled_for=occurrence.isoformat(),
                    payload=json.dumps(dict(schedule.metadata or {}), sort_keys=True),
                    created_at=current.isoformat(),
                ):
                    created.append(
                        Job(
                            job_id,
                            schedule.schedule_id,
                            schedule.workspace_id,
                            occurrence,
                            JobState.QUEUED,
                            0,
                            dict(schedule.metadata or {}),
                        )
                    )
            next_run = self._next_after(schedule, current)
            self.store.update_scheduler_schedule(
                schedule.schedule_id,
                expected_generation=schedule.generation,
                enabled=schedule.enabled and schedule.kind not in {
                    ScheduleKind.ONE_SHOT,
                    ScheduleKind.CALENDAR,
                },
                next_run_at=next_run.isoformat() if next_run else current.isoformat(),
                last_run_at=current.isoformat(),
                generation=schedule.generation + 1,
                expression=schedule.expression,
                timezone=schedule.timezone,
                misfire_policy=schedule.misfire_policy.value,
                max_concurrency=schedule.max_concurrency,
                metadata=json.dumps(dict(schedule.metadata or {}), sort_keys=True),
                updated_at=current.isoformat(),
            )
        return tuple(created)

    def lease_due(
        self,
        *,
        owner: str,
        lease_seconds: int = 300,
        now: datetime | None = None,
        limit: int = 100,
    ) -> tuple[Job, ...]:
        if not owner:
            raise ValueError("lease owner is required")
        if lease_seconds < 1:
            raise ValueError("lease_seconds must be positive")
        current = self._now(now)
        self.store.release_expired_scheduler_jobs(current.isoformat())
        leased: list[Job] = []
        for row in self.store.due_scheduler_jobs(current.isoformat(), limit):
            schedule = self.get(row["schedule_id"])
            running = self.store.query(
                "SELECT COUNT(*) AS count FROM scheduler_jobs "
                "WHERE schedule_id=? AND state='running'",
                (schedule.schedule_id,),
            )[0]["count"]
            if int(running) >= schedule.max_concurrency:
                continue
            if self.store.lease_scheduler_job(
                row["job_id"],
                owner,
                (current + timedelta(seconds=lease_seconds)).isoformat(),
                current.isoformat(),
            ):
                leased.append(self._job_from_row(self.store.get_scheduler_job(row["job_id"])))
        return tuple(leased)

    def dispatch_due(
        self,
        dispatcher: Callable[[Job], None],
        *,
        owner: str,
        lease_seconds: int = 300,
        now: datetime | None = None,
        limit: int = 100,
    ) -> SchedulerRun:
        created = self.reconcile(now=now, limit=limit)
        leased = self.lease_due(
            owner=owner, lease_seconds=lease_seconds, now=now, limit=limit
        )
        for job in leased:
            try:
                dispatcher(job)
            except Exception as exc:
                current = self._now(now)
                self.store.finish_scheduler_job(
                    job.job_id,
                    state=JobState.FAILED.value,
                    error=str(exc)[:2000],
                    finished_at=current.isoformat(),
                    now=current.isoformat(),
                )
            else:
                current = self._now(now)
                self.store.finish_scheduler_job(
                    job.job_id,
                    state=JobState.SUCCEEDED.value,
                    error=None,
                    finished_at=current.isoformat(),
                    now=current.isoformat(),
                )
        return SchedulerRun(created, leased)

    def _first_occurrence(self, schedule: Schedule, now: datetime) -> datetime:
        local_now = now.astimezone(ZoneInfo(schedule.timezone))
        if schedule.kind is ScheduleKind.INTERVAL:
            seconds = self._interval_seconds(schedule.expression)
            return local_now + timedelta(seconds=seconds)
        if schedule.kind in {ScheduleKind.ONE_SHOT, ScheduleKind.CALENDAR}:
            return self._parse_datetime(schedule.expression, schedule.timezone)
        return CronExpression(schedule.expression).next_after(local_now)

    def _next_after(self, schedule: Schedule, now: datetime) -> datetime | None:
        if schedule.kind in {ScheduleKind.ONE_SHOT, ScheduleKind.CALENDAR}:
            return None
        local = now.astimezone(ZoneInfo(schedule.timezone))
        if schedule.kind is ScheduleKind.INTERVAL:
            return local + timedelta(seconds=self._interval_seconds(schedule.expression))
        return CronExpression(schedule.expression).next_after(local).astimezone(UTC)

    def _due_occurrences(self, schedule: Schedule, now: datetime) -> tuple[datetime, ...]:
        due = datetime.fromisoformat(
            self.store.get_scheduler_schedule(schedule.schedule_id)["next_run_at"]
        ).astimezone(UTC)
        if due > now.astimezone(UTC):
            return ()
        if schedule.misfire_policy is not MisfirePolicy.CATCH_UP:
            return (due,)
        occurrences: list[datetime] = []
        cursor = due
        for _ in range(100):
            if cursor > now.astimezone(UTC):
                break
            occurrences.append(cursor)
            cursor = self._next_after(schedule, cursor)
            if cursor is None:
                break
        return tuple(occurrences)

    @staticmethod
    def _interval_seconds(expression: str) -> int:
        seconds = int(expression)
        if seconds < 1:
            raise ValueError("interval seconds must be positive")
        return seconds

    @staticmethod
    def _parse_datetime(expression: str, timezone: str) -> datetime:
        value = datetime.fromisoformat(expression)
        if value.tzinfo is None:
            value = value.replace(tzinfo=ZoneInfo(timezone))
        return value

    @staticmethod
    def _with_next(
        schedule: Schedule, next_run: datetime, generation: int | None = None
    ) -> Schedule:
        return Schedule(
            schedule_id=schedule.schedule_id,
            workspace_id=schedule.workspace_id,
            name=schedule.name,
            kind=schedule.kind,
            expression=schedule.expression,
            timezone=schedule.timezone,
            enabled=schedule.enabled,
            misfire_policy=schedule.misfire_policy,
            max_concurrency=schedule.max_concurrency,
            next_run_at=next_run,
            generation=generation or schedule.generation,
            metadata=schedule.metadata or {},
        )

    @staticmethod
    def _now(value: datetime | None) -> datetime:
        current = value or datetime.now(UTC)
        if current.tzinfo is None:
            raise ValueError("scheduler time must be timezone-aware")
        return current.astimezone(UTC)

    @staticmethod
    def _schedule_from_row(row: Mapping[str, object]) -> Schedule:
        return Schedule(
            schedule_id=str(row["schedule_id"]),
            workspace_id=str(row["workspace_id"]),
            name=str(row["name"]),
            kind=ScheduleKind(str(row["kind"])),
            expression=str(row["expression"]),
            timezone=str(row["timezone"]),
            enabled=bool(row["enabled"]),
            misfire_policy=MisfirePolicy(str(row["misfire_policy"])),
            max_concurrency=int(row["max_concurrency"]),
            next_run_at=datetime.fromisoformat(str(row["next_run_at"])),
            generation=int(row["generation"]),
            metadata=json.loads(str(row["metadata"])),
        )

    @staticmethod
    def _job_from_row(row: Mapping[str, object] | None) -> Job:
        if row is None:
            raise KeyError("scheduler job disappeared during lease")
        return Job(
            job_id=str(row["job_id"]),
            schedule_id=str(row["schedule_id"]),
            workspace_id=str(row["workspace_id"]),
            scheduled_for=datetime.fromisoformat(str(row["scheduled_for"])),
            state=JobState(str(row["state"])),
            attempt=int(row["attempt"]),
            payload=json.loads(str(row["payload"])),
            error=str(row["error"]) if row["error"] is not None else None,
        )
