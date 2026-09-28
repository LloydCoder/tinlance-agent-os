"""Core Agent OS domain contracts.

These types describe OS-level state. They intentionally do not grant authority;
consequential execution is delegated to Tinlance Agent Platform.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum


def utc_now() -> datetime:
    return datetime.now(UTC)


class SessionState(StrEnum):
    ACTIVE = "active"
    PAUSED = "paused"
    CLOSED = "closed"


class TaskState(StrEnum):
    CREATED = "created"
    READY = "ready"
    RUNNING = "running"
    WAITING_APPROVAL = "waiting_approval"
    WAITING_INPUT = "waiting_input"
    BLOCKED = "blocked"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    EXPIRED = "expired"


@dataclass(frozen=True, slots=True)
class User:
    user_id: str


@dataclass(frozen=True, slots=True)
class Workspace:
    workspace_id: str
    owner_user_id: str


@dataclass(frozen=True, slots=True)
class Agent:
    agent_id: str
    name: str
    version: str


@dataclass(frozen=True, slots=True)
class Session:
    session_id: str
    workspace_id: str
    user_id: str
    agent_id: str
    state: SessionState = SessionState.ACTIVE


@dataclass(frozen=True, slots=True)
class Task:
    task_id: str
    workspace_id: str
    session_id: str
    agent_id: str
    intent: str
    state: TaskState = TaskState.CREATED
    dependencies: Sequence[str] = field(default_factory=tuple)
    platform_run_ids: Sequence[str] = field(default_factory=tuple)
    created_at: datetime = field(default_factory=utc_now)


@dataclass(frozen=True, slots=True)
class PlatformRunRef:
    run_id: str
    task_id: str
    state: str


@dataclass(frozen=True, slots=True)
class CapabilityRef:
    capability_id: str
    source: str = "agent-platform"


@dataclass(frozen=True, slots=True)
class ApprovalRef:
    approval_id: str
    source: str = "agent-platform"


@dataclass(frozen=True, slots=True)
class EvidenceRef:
    evidence_id: str
    source: str = "agent-platform"


@dataclass(frozen=True, slots=True)
class Event:
    event_id: str
    event_type: str
    occurred_at: datetime
    workspace_id: str
    session_id: str | None
    task_id: str | None
    agent_id: str | None
    platform_run_id: str | None
    correlation_id: str
    source: str
    payload: Mapping[str, object] = field(default_factory=dict)
