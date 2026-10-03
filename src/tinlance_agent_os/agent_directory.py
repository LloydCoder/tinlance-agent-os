"""M26 agent directory and desired-state reconciliation.

The directory owns what an Agent OS workspace intends to have deployed. It does not
authorize, execute, or grant capabilities; consequential execution remains owned by
Tinlance Agent Platform.
"""

from __future__ import annotations

import json
import re
import sqlite3
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from collections.abc import Mapping

from .agent_runtime import AgentLifecycleState, HealthState
from .store import StateStore


_VERSION_RE = re.compile(r"^\d+\.\d+\.\d+$")


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _version_key(value: str) -> tuple[int, int, int]:
    if not _VERSION_RE.fullmatch(value):
        raise ValueError("version must use numeric major.minor.patch notation")
    return tuple(int(part) for part in value.split("."))  # type: ignore[return-value]


class DesiredAgentState(StrEnum):
    RUNNING = "running"
    PAUSED = "paused"
    STOPPED = "stopped"


class ReconciliationAction(StrEnum):
    NOOP = "noop"
    START = "start"
    PAUSE = "pause"
    STOP = "stop"
    UPGRADE = "upgrade"
    RECONFIGURE = "reconfigure"
    BLOCKED = "blocked"


@dataclass(frozen=True, slots=True)
class Compatibility:
    minimum_os_version: str = "0.1.0"
    platform_contract: str = "1.1"
    python: str = ">=3.12"

    def validate(self) -> None:
        _version_key(self.minimum_os_version)
        if not self.platform_contract.strip():
            raise ValueError("platform_contract is required")
        if not self.python.strip():
            raise ValueError("python compatibility is required")


@dataclass(frozen=True, slots=True)
class DesiredAgent:
    agent_id: str
    workspace_id: str
    name: str
    version: str
    entrypoint: str
    desired_state: DesiredAgentState = DesiredAgentState.RUNNING
    capabilities: tuple[str, ...] = ()
    configuration: Mapping[str, object] = field(default_factory=dict)
    compatibility: Compatibility = field(default_factory=Compatibility)
    rollout_channel: str = "stable"
    generation: int = 1

    def validate(self) -> None:
        for name in ("agent_id", "workspace_id", "name", "entrypoint", "rollout_channel"):
            if not getattr(self, name).strip():
                raise ValueError(f"{name} is required")
        _version_key(self.version)
        if self.generation < 1:
            raise ValueError("generation must be >= 1")
        if len(self.capabilities) != len(set(self.capabilities)):
            raise ValueError("capabilities must be unique")
        if any(not item.strip() for item in self.capabilities):
            raise ValueError("capabilities must be non-empty")
        self.compatibility.validate()
        try:
            json.dumps(dict(self.configuration), sort_keys=True)
        except (TypeError, ValueError) as exc:
            raise ValueError("configuration must be JSON serializable") from exc


@dataclass(frozen=True, slots=True)
class AgentObservation:
    agent_id: str
    workspace_id: str
    name: str
    version: str
    state: AgentLifecycleState
    health: HealthState
    state_version: int
    configuration: Mapping[str, object]
    capabilities: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class ReconciliationPlan:
    agent_id: str
    generation: int
    action: ReconciliationAction
    reason: str


class AgentDirectory:
    """Durable desired-state registry with read-only reconciliation planning."""

    def __init__(self, store: StateStore) -> None:
        self.store = store
        self._ensure_schema()

    def set_desired(
        self,
        desired: DesiredAgent,
        *,
        expected_generation: int | None = None,
    ) -> DesiredAgent:
        desired.validate()
        if expected_generation is not None and expected_generation < 1:
            raise ValueError("expected_generation must be >= 1")
        now = _now()
        encoded_capabilities = json.dumps(desired.capabilities, sort_keys=True)
        encoded_configuration = json.dumps(dict(desired.configuration), sort_keys=True)
        encoded_compatibility = json.dumps(
            {
                "minimum_os_version": desired.compatibility.minimum_os_version,
                "platform_contract": desired.compatibility.platform_contract,
                "python": desired.compatibility.python,
            },
            sort_keys=True,
        )
        with sqlite3.connect(self.store.path) as db:
            db.execute("PRAGMA foreign_keys=ON")
            row = db.execute(
                "SELECT generation FROM agent_desired_state WHERE agent_id = ?",
                (desired.agent_id,),
            ).fetchone()
            current = int(row[0]) if row else None
            if expected_generation is not None and current != expected_generation:
                raise ValueError("desired agent generation conflict")
            generation = (current + 1) if current is not None else desired.generation
            db.execute(
                """
                INSERT INTO agent_desired_state (
                    agent_id, workspace_id, name, version, entrypoint, desired_state,
                    capabilities, configuration, compatibility, rollout_channel,
                    generation, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(agent_id) DO UPDATE SET
                    workspace_id=excluded.workspace_id,
                    name=excluded.name,
                    version=excluded.version,
                    entrypoint=excluded.entrypoint,
                    desired_state=excluded.desired_state,
                    capabilities=excluded.capabilities,
                    configuration=excluded.configuration,
                    compatibility=excluded.compatibility,
                    rollout_channel=excluded.rollout_channel,
                    generation=excluded.generation,
                    updated_at=excluded.updated_at
                """,
                (
                    desired.agent_id,
                    desired.workspace_id,
                    desired.name,
                    desired.version,
                    desired.entrypoint,
                    desired.desired_state.value,
                    encoded_capabilities,
                    encoded_configuration,
                    encoded_compatibility,
                    desired.rollout_channel,
                    generation,
                    now,
                ),
            )
        return DesiredAgent(
            desired.agent_id,
            desired.workspace_id,
            desired.name,
            desired.version,
            desired.entrypoint,
            desired.desired_state,
            desired.capabilities,
            dict(desired.configuration),
            desired.compatibility,
            desired.rollout_channel,
            generation,
        )

    def get_desired(self, agent_id: str) -> DesiredAgent | None:
        row = self.store.query(
            "SELECT * FROM agent_desired_state WHERE agent_id = ?",
            (agent_id,),
        )
        if not row:
            return None
        item = row[0]
        compatibility = Compatibility(**json.loads(item["compatibility"]))
        return DesiredAgent(
            item["agent_id"],
            item["workspace_id"],
            item["name"],
            item["version"],
            item["entrypoint"],
            DesiredAgentState(item["desired_state"]),
            tuple(json.loads(item["capabilities"])),
            json.loads(item["configuration"]),
            compatibility,
            item["rollout_channel"],
            int(item["generation"]),
        )

    def observe(self, agent_id: str) -> AgentObservation | None:
        row = self.store.get_agent(agent_id)
        if row is None:
            return None
        return AgentObservation(
            row["agent_id"],
            row["workspace_id"],
            row["name"],
            row["version"],
            AgentLifecycleState(row["state"]),
            HealthState(row["health_state"]),
            int(row["state_version"]),
            json.loads(row["configuration"]),
            tuple(json.loads(row["capabilities"])),
        )

    def plan(self, agent_id: str) -> ReconciliationPlan:
        desired = self.get_desired(agent_id)
        if desired is None:
            raise ValueError("desired agent state is not registered")
        observed = self.observe(agent_id)
        if observed is None:
            return ReconciliationPlan(
                agent_id,
                desired.generation,
                ReconciliationAction.BLOCKED,
                "agent is not registered with the lifecycle runtime",
            )
        if observed.workspace_id != desired.workspace_id:
            return ReconciliationPlan(
                agent_id,
                desired.generation,
                ReconciliationAction.BLOCKED,
                "workspace identity differs between desired and observed state",
            )
        if observed.version != desired.version:
            return ReconciliationPlan(
                agent_id,
                desired.generation,
                ReconciliationAction.UPGRADE,
                f"observed version {observed.version} differs from desired {desired.version}",
            )
        if dict(observed.configuration) != dict(desired.configuration):
            return ReconciliationPlan(
                agent_id,
                desired.generation,
                ReconciliationAction.RECONFIGURE,
                "observed configuration differs from desired configuration",
            )
        if observed.capabilities != desired.capabilities:
            return ReconciliationPlan(
                agent_id,
                desired.generation,
                ReconciliationAction.RECONFIGURE,
                "observed capabilities differ from desired capabilities",
            )
        if desired.desired_state is DesiredAgentState.RUNNING:
            if (
                observed.state is AgentLifecycleState.RUNNING
                and observed.health is HealthState.HEALTHY
            ):
                return ReconciliationPlan(
                    agent_id,
                    desired.generation,
                    ReconciliationAction.NOOP,
                    "in desired state",
                )
            return ReconciliationPlan(
                agent_id,
                desired.generation,
                ReconciliationAction.START,
                "agent should be running",
            )
        if desired.desired_state is DesiredAgentState.PAUSED:
            if observed.state is AgentLifecycleState.PAUSED:
                return ReconciliationPlan(
                    agent_id,
                    desired.generation,
                    ReconciliationAction.NOOP,
                    "in desired state",
                )
            return ReconciliationPlan(
                agent_id,
                desired.generation,
                ReconciliationAction.PAUSE,
                "agent should be paused",
            )
        if observed.state is AgentLifecycleState.STOPPED:
            return ReconciliationPlan(
                agent_id,
                desired.generation,
                ReconciliationAction.NOOP,
                "in desired state",
            )
        return ReconciliationPlan(
            agent_id,
            desired.generation,
            ReconciliationAction.STOP,
            "agent should be stopped",
        )

    def list_desired(self, workspace_id: str) -> tuple[DesiredAgent, ...]:
        rows = self.store.query(
            "SELECT agent_id FROM agent_desired_state WHERE workspace_id = ? ORDER BY agent_id",
            (workspace_id,),
        )
        return tuple(
            item
            for row in rows
            if (item := self.get_desired(row["agent_id"])) is not None
        )

    def _ensure_schema(self) -> None:
        with sqlite3.connect(self.store.path) as db:
            db.execute(
                """
                CREATE TABLE IF NOT EXISTS agent_desired_state (
                    agent_id TEXT PRIMARY KEY,
                    workspace_id TEXT NOT NULL,
                    name TEXT NOT NULL,
                    version TEXT NOT NULL,
                    entrypoint TEXT NOT NULL,
                    desired_state TEXT NOT NULL,
                    capabilities TEXT NOT NULL,
                    configuration TEXT NOT NULL,
                    compatibility TEXT NOT NULL,
                    rollout_channel TEXT NOT NULL,
                    generation INTEGER NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            db.execute(
                "CREATE INDEX IF NOT EXISTS idx_agent_desired_workspace "
                "ON agent_desired_state(workspace_id, desired_state, updated_at)"
            )
