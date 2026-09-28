"""Core Agent OS domain contracts.

These models describe OS-level lifecycle and composition. They do not grant
execution authority; governed authority remains in Tinlance Agent Platform.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from typing import NewType

UserId = NewType("UserId", str)
WorkspaceId = NewType("WorkspaceId", str)
SessionId = NewType("SessionId", str)
AgentId = NewType("AgentId", str)
TaskId = NewType("TaskId", str)
RunId = NewType("RunId", str)
EventId = NewType("EventId", str)
CorrelationId = NewType("CorrelationId", str)


class TaskStatus(StrEnum):
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
    user_id: UserId


@dataclass(frozen=True, slots=True)
class Workspace:
    workspace_id: WorkspaceId
    owner_id: UserId


@dataclass(frozen=True, slots=True)
class Session:
    session_id: SessionId
    workspace_id: WorkspaceId
    user_id: UserId
    agent_id: AgentId


@dataclass(frozen=True, slots=True)
class Agent:
    agent_id: AgentId
    name: str
    version: str


@dataclass(frozen=True, slots=True)
class Task:
    task_id: TaskId
    workspace_id: WorkspaceId
    session_id: SessionId
    agent_id: AgentId
    intent: str
    status: TaskStatus = TaskStatus.CREATED
    platform_run_ids: tuple[RunId, ...] = field(default_factory=tuple)


@dataclass(frozen=True, slots=True)
class Event:
    event_id: EventId
    event_type: str
    occurred_at: datetime
    workspace_id: WorkspaceId
    correlation_id: CorrelationId
    platform_run_id: RunId | None
    source: str
    payload: object
