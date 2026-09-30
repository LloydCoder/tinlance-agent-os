"""Durable Agent OS runtime and lifecycle state machine (M12)."""

from __future__ import annotations

import hashlib
import json
import sqlite3
import threading
import time
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from enum import StrEnum

from .store import StateStore


def _now() -> datetime:
    return datetime.now(UTC)


class AgentLifecycleState(StrEnum):
    REGISTERED = "registered"
    VALIDATING = "validating"
    READY = "ready"
    STARTING = "starting"
    RUNNING = "running"
    PAUSING = "pausing"
    PAUSED = "paused"
    RESUMING = "resuming"
    STOPPING = "stopping"
    STOPPED = "stopped"
    CRASHED = "crashed"
    RECOVERING = "recovering"
    FAILED = "failed"


class HealthState(StrEnum):
    UNKNOWN = "unknown"
    HEALTHY = "healthy"
    UNHEALTHY = "unhealthy"
    CRASHED = "crashed"
    STOPPED = "stopped"


@dataclass(frozen=True, slots=True)
class RestartPolicy:
    enabled: bool = True
    max_restarts: int = 3
    backoff_seconds: float = 0.0

    def validate(self) -> None:
        if self.max_restarts < 0:
            raise ValueError("max_restarts must be >= 0")
        if self.backoff_seconds < 0:
            raise ValueError("backoff_seconds must be >= 0")


@dataclass(frozen=True, slots=True)
class RuntimeConfig:
    heartbeat_interval_seconds: float = 5.0
    heartbeat_timeout_seconds: float = 15.0
    shutdown_timeout_seconds: float = 10.0

    def validate(self) -> None:
        if self.heartbeat_interval_seconds <= 0:
            raise ValueError("heartbeat_interval_seconds must be > 0")
        if self.heartbeat_timeout_seconds < self.heartbeat_interval_seconds:
            raise ValueError("heartbeat_timeout_seconds must be >= heartbeat_interval_seconds")
        if self.shutdown_timeout_seconds <= 0:
            raise ValueError("shutdown_timeout_seconds must be > 0")


@dataclass(frozen=True, slots=True)
class AgentDefinition:
    agent_id: str
    workspace_id: str
    name: str
    version: str
    entrypoint: str
    capabilities: tuple[str, ...] = ()
    configuration: Mapping[str, object] = field(default_factory=dict)
    restart_policy: RestartPolicy = field(default_factory=RestartPolicy)
    runtime: RuntimeConfig = field(default_factory=RuntimeConfig)

    def validate(self) -> None:
        for field_name in ("agent_id", "workspace_id", "name", "version", "entrypoint"):
            if not getattr(self, field_name).strip():
                raise ValueError(f"{field_name} is required")
        if len(self.capabilities) != len(set(self.capabilities)):
            raise ValueError("capabilities must be unique")
        if any(not capability.strip() for capability in self.capabilities):
            raise ValueError("capabilities must be non-empty")
        self.restart_policy.validate()
        self.runtime.validate()
        try:
            json.dumps(dict(self.configuration), sort_keys=True)
        except (TypeError, ValueError) as exc:
            raise ValueError("configuration must be JSON serializable") from exc


@dataclass(frozen=True, slots=True)
class AgentSnapshot:
    definition: AgentDefinition
    state: AgentLifecycleState
    health: HealthState
    state_version: int
    restart_count: int
    last_heartbeat_at: datetime | None
    lease_expires_at: datetime | None


_TRANSITIONS: dict[AgentLifecycleState, frozenset[AgentLifecycleState]] = {
    AgentLifecycleState.REGISTERED: frozenset({AgentLifecycleState.VALIDATING}),
    AgentLifecycleState.VALIDATING: frozenset(
        {
            AgentLifecycleState.READY,
            AgentLifecycleState.FAILED,
        }
    ),
    AgentLifecycleState.READY: frozenset(
        {
            AgentLifecycleState.STARTING,
            AgentLifecycleState.STOPPED,
        }
    ),
    AgentLifecycleState.STARTING: frozenset(
        {
            AgentLifecycleState.RUNNING,
            AgentLifecycleState.CRASHED,
        }
    ),
    AgentLifecycleState.RUNNING: frozenset(
        {
            AgentLifecycleState.PAUSING,
            AgentLifecycleState.STOPPING,
            AgentLifecycleState.CRASHED,
        }
    ),
    AgentLifecycleState.PAUSING: frozenset(
        {
            AgentLifecycleState.PAUSED,
            AgentLifecycleState.CRASHED,
        }
    ),
    AgentLifecycleState.PAUSED: frozenset(
        {
            AgentLifecycleState.RESUMING,
            AgentLifecycleState.STOPPING,
        }
    ),
    AgentLifecycleState.RESUMING: frozenset(
        {
            AgentLifecycleState.RUNNING,
            AgentLifecycleState.CRASHED,
        }
    ),
    AgentLifecycleState.STOPPING: frozenset(
        {
            AgentLifecycleState.STOPPED,
            AgentLifecycleState.CRASHED,
        }
    ),
    AgentLifecycleState.STOPPED: frozenset(
        {
            AgentLifecycleState.STARTING,
            AgentLifecycleState.RECOVERING,
        }
    ),
    AgentLifecycleState.CRASHED: frozenset(
        {
            AgentLifecycleState.RECOVERING,
            AgentLifecycleState.FAILED,
        }
    ),
    AgentLifecycleState.RECOVERING: frozenset(
        {
            AgentLifecycleState.STARTING,
            AgentLifecycleState.FAILED,
        }
    ),
    AgentLifecycleState.FAILED: frozenset(),
}
