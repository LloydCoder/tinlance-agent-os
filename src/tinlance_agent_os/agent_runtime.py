"""Durable Agent OS runtime and lifecycle state machine (M12)."""

from __future__ import annotations
from .observability import telemetry

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


class AgentRuntime:
    """Owns one agent's lifecycle; authority remains outside the runtime."""

    def __init__(
        self,
        store: StateStore,
        definition: AgentDefinition,
        worker: Callable[[Mapping[str, object]], object],
    ) -> None:
        definition.validate()
        self.store = store
        self.definition = definition
        self.worker = worker
        self._stop_event = threading.Event()
        self._heartbeat_thread: threading.Thread | None = None
        self._lock = threading.RLock()

    def register(self) -> AgentSnapshot:
        self.definition.validate()
        existing = self.store.get_agent(self.definition.agent_id)
        if existing is not None and existing["version"] != self.definition.version:
            raise ValueError("agent version is already bound to a different registered version")
        now = _now()
        self.store.register_agent(self.definition, now.isoformat())
        return self.snapshot()

    def validate(self) -> AgentSnapshot:
        with self._lock:
            self._require_state(AgentLifecycleState.REGISTERED)
            self._transition(AgentLifecycleState.VALIDATING, "agent.validation.started")
            try:
                self.definition.validate()
                self._transition(AgentLifecycleState.READY, "agent.validation.succeeded")
            except Exception:
                self._transition(AgentLifecycleState.FAILED, "agent.validation.failed")
                raise
            return self.snapshot()

    def start(self) -> AgentSnapshot:
        with telemetry().span(
            "agentos.agent.start",
            {"gen_ai.agent.id": self.definition.agent_id},
        ):
            with self._lock:
                self._require_state(
                    AgentLifecycleState.READY,
                    AgentLifecycleState.STOPPED,
                )
                self._transition(AgentLifecycleState.STARTING, "agent.starting")
                try:
                    self._transition(AgentLifecycleState.RUNNING, "agent.started")
                    self._start_heartbeat()
                except Exception:
                    self._stop_heartbeat()
                    self._transition(AgentLifecycleState.CRASHED, "agent.start.failed")
                    raise
                return self.snapshot()

    def run(self) -> object:
        with telemetry().span(
            "gen_ai.invoke_agent",
            {"gen_ai.agent.id": self.definition.agent_id},
        ):
            with self._lock:
                self._require_state(AgentLifecycleState.RUNNING)
            try:
                return self.worker(dict(self.definition.configuration))
            except Exception as exc:
                with self._lock:
                    self._transition(
                        AgentLifecycleState.CRASHED,
                        "agent.crashed",
                        payload={"error": type(exc).__name__},
                    )
                    self._stop_heartbeat()
                if self.definition.restart_policy.enabled:
                    self.recover()
                raise

    def pause(self) -> AgentSnapshot:
        with self._lock:
            self._require_state(AgentLifecycleState.RUNNING)
            self._transition(AgentLifecycleState.PAUSING, "agent.pausing")
            self._stop_heartbeat()
            self._transition(AgentLifecycleState.PAUSED, "agent.paused")
            return self.snapshot()

    def resume(self) -> AgentSnapshot:
        with self._lock:
            self._require_state(AgentLifecycleState.PAUSED)
            self._transition(AgentLifecycleState.RESUMING, "agent.resuming")
            self._transition(AgentLifecycleState.RUNNING, "agent.resumed")
            self._start_heartbeat()
            return self.snapshot()

    def stop(self) -> AgentSnapshot:
        with self._lock:
            self._require_state(
                AgentLifecycleState.RUNNING,
                AgentLifecycleState.PAUSED,
                AgentLifecycleState.CRASHED,
                AgentLifecycleState.READY,
            )
            self._transition(AgentLifecycleState.STOPPING, "agent.stopping")
            self._stop_heartbeat()
            self._transition(AgentLifecycleState.STOPPED, "agent.stopped")
            return self.snapshot()

    def recover(self) -> AgentSnapshot:
        with self._lock:
            self._require_state(AgentLifecycleState.CRASHED, AgentLifecycleState.STOPPED)
            row = self.store.get_agent(self.definition.agent_id)
            if row is None:
                raise ValueError("agent is not registered")
            restart_count = int(row["restart_count"])
            if (
                self.definition.restart_policy.enabled
                and restart_count >= self.definition.restart_policy.max_restarts
            ):
                self._transition(AgentLifecycleState.FAILED, "agent.recovery.exhausted")
                return self.snapshot()
            self._transition(AgentLifecycleState.RECOVERING, "agent.recovery.started")
            if self.definition.restart_policy.backoff_seconds:
                self._stop_heartbeat()
                time.sleep(self.definition.restart_policy.backoff_seconds)
            self.store.increment_agent_restart(self.definition.agent_id)
            self._transition(AgentLifecycleState.STARTING, "agent.recovery.starting")
            self._transition(AgentLifecycleState.RUNNING, "agent.recovered")
            self._start_heartbeat()
            return self.snapshot()

    def heartbeat(self) -> AgentSnapshot:
        with self._lock:
            self._require_state(AgentLifecycleState.RUNNING)
            now = _now()
            self.store.record_agent_heartbeat(
                self.definition.agent_id,
                now.isoformat(),
                (
                    now + timedelta(seconds=self.definition.runtime.heartbeat_timeout_seconds)
                ).isoformat(),
            )
            return self.snapshot()

    def health(self) -> HealthState:
        row = self.store.get_agent(self.definition.agent_id)
        if row is None:
            raise ValueError("agent is not registered")
        lease = row["lease_expires_at"]
        if (
            row["state"] == AgentLifecycleState.RUNNING.value
            and isinstance(lease, str)
            and datetime.fromisoformat(lease) < _now()
        ):
            return HealthState.UNHEALTHY
        return HealthState(row["health_state"])

    def snapshot(self) -> AgentSnapshot:
        row = self.store.get_agent(self.definition.agent_id)
        if row is None:
            raise ValueError("agent is not registered")
        bound = AgentDefinition(
            row["agent_id"],
            row["workspace_id"],
            row["name"],
            row["version"],
            row["entrypoint"],
            tuple(json.loads(row["capabilities"])),
            json.loads(row["configuration"]),
            RestartPolicy(**json.loads(row["restart_policy"])),
            RuntimeConfig(**json.loads(row["runtime_config"])),
        )
        return AgentSnapshot(
            bound,
            AgentLifecycleState(row["state"]),
            HealthState(row["health_state"]),
            int(row["state_version"]),
            int(row["restart_count"]),
            datetime.fromisoformat(row["last_heartbeat_at"]) if row["last_heartbeat_at"] else None,
            datetime.fromisoformat(row["lease_expires_at"]) if row["lease_expires_at"] else None,
        )

    def _require_state(self, *allowed: AgentLifecycleState) -> None:
        state = self.snapshot().state
        if state not in allowed:
            raise ValueError(f"invalid lifecycle operation from {state.value}")

    def _transition(
        self,
        new_state: AgentLifecycleState,
        event_type: str,
        *,
        now: datetime | None = None,
        payload: Mapping[str, object] | None = None,
    ) -> None:
        current = self.snapshot().state
        if new_state not in _TRANSITIONS[current]:
            raise ValueError(f"invalid lifecycle transition {current.value} -> {new_state.value}")
        occurred_at = now or _now()
        self.store.transition_agent(
            self.definition.agent_id,
            current.value,
            new_state.value,
            occurred_at.isoformat(),
            event_type,
            dict(payload or {}),
        )

    def _start_heartbeat(self) -> None:
        self._stop_event.clear()
        self.heartbeat()
        if self._heartbeat_thread is None or not self._heartbeat_thread.is_alive():
            self._heartbeat_thread = threading.Thread(
                target=self._heartbeat_loop,
                name=f"agent-heartbeat-{self.definition.agent_id}",
                daemon=True,
            )
            self._heartbeat_thread.start()

    def _stop_heartbeat(self) -> None:
        self._stop_event.set()
        thread = self._heartbeat_thread
        if thread is not None and thread is not threading.current_thread():
            thread.join(timeout=self.definition.runtime.shutdown_timeout_seconds)
        self._heartbeat_thread = None

    def _heartbeat_loop(self) -> None:
        while not self._stop_event.wait(self.definition.runtime.heartbeat_interval_seconds):
            try:
                self.heartbeat()
            except (ValueError, sqlite3.Error):
                return

    @staticmethod
    def deterministic_event_id(agent_id: str, sequence: int, event_type: str) -> str:
        return hashlib.sha256(f"agent:{agent_id}:{sequence}:{event_type}".encode()).hexdigest()


def recover_orphans(store: StateStore, *, now: datetime | None = None) -> tuple[str, ...]:
    """Mark expired running agents crashed after a process restart."""
    recovered: list[str] = []
    moment = now or _now()
    for row in store.running_agents():
        lease = row["lease_expires_at"]
        if not isinstance(lease, str) or datetime.fromisoformat(lease) >= moment:
            continue
        store.transition_agent(
            row["agent_id"],
            AgentLifecycleState.RUNNING.value,
            AgentLifecycleState.CRASHED.value,
            moment.isoformat(),
            "agent.crash.detected",
            {"reason": "heartbeat_lease_expired"},
        )
        recovered.append(row["agent_id"])
    return tuple(recovered)
