"""Durable local Agent OS state store with explicit query/write boundaries."""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True, slots=True)
class StateStore:
    path: Path

    def __post_init__(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(self.path) as db:
            db.execute("PRAGMA foreign_keys=ON")
            db.execute("PRAGMA journal_mode=WAL")
            db.execute("PRAGMA synchronous=FULL")
            db.executescript(
                """
                CREATE TABLE IF NOT EXISTS workspaces (
                    workspace_id TEXT PRIMARY KEY,
                    owner_user_id TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS sessions (
                    session_id TEXT PRIMARY KEY,
                    workspace_id TEXT NOT NULL REFERENCES workspaces(workspace_id),
                    user_id TEXT NOT NULL,
                    agent_id TEXT NOT NULL,
                    state TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS tasks (
                    task_id TEXT PRIMARY KEY,
                    workspace_id TEXT NOT NULL REFERENCES workspaces(workspace_id),
                    session_id TEXT NOT NULL REFERENCES sessions(session_id),
                    agent_id TEXT NOT NULL,
                    intent TEXT NOT NULL,
                    state TEXT NOT NULL,
                    dependencies TEXT NOT NULL,
                    platform_run_ids TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS events (
                    event_id TEXT PRIMARY KEY,
                    event_type TEXT NOT NULL,
                    occurred_at TEXT NOT NULL,
                    workspace_id TEXT NOT NULL REFERENCES workspaces(workspace_id),
                    session_id TEXT REFERENCES sessions(session_id),
                    task_id TEXT REFERENCES tasks(task_id),
                    agent_id TEXT,
                    platform_run_id TEXT,
                    correlation_id TEXT NOT NULL,
                    source TEXT NOT NULL,
                    payload TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS memory (
                    memory_id TEXT PRIMARY KEY,
                    workspace_id TEXT NOT NULL REFERENCES workspaces(workspace_id),
                    scope TEXT NOT NULL,
                    classification TEXT NOT NULL,
                    content TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS workflows (
                    workflow_id TEXT PRIMARY KEY,
                    workspace_id TEXT NOT NULL REFERENCES workspaces(workspace_id),
                    definition TEXT NOT NULL,
                    state TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS agents (
                    agent_id TEXT PRIMARY KEY,
                    workspace_id TEXT NOT NULL,
                    name TEXT NOT NULL,
                    version TEXT NOT NULL,
                    entrypoint TEXT NOT NULL,
                    capabilities TEXT NOT NULL,
                    configuration TEXT NOT NULL,
                    restart_policy TEXT NOT NULL,
                    runtime_config TEXT NOT NULL,
                    state TEXT NOT NULL,
                    health_state TEXT NOT NULL,
                    state_version INTEGER NOT NULL,
                    restart_count INTEGER NOT NULL,
                    last_heartbeat_at TEXT,
                    lease_expires_at TEXT,
                    registered_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS agent_lifecycle_events (
                    event_id TEXT PRIMARY KEY,
                    agent_id TEXT NOT NULL REFERENCES agents(agent_id),
                    workspace_id TEXT NOT NULL,
                    sequence INTEGER NOT NULL,
                    event_type TEXT NOT NULL,
                    from_state TEXT,
                    to_state TEXT NOT NULL,
                    occurred_at TEXT NOT NULL,
                    correlation_id TEXT NOT NULL,
                    payload TEXT NOT NULL,
                    UNIQUE(agent_id, sequence)
                );
                CREATE INDEX IF NOT EXISTS idx_sessions_workspace ON sessions(workspace_id);
                CREATE INDEX IF NOT EXISTS idx_tasks_workspace ON tasks(workspace_id);
                CREATE INDEX IF NOT EXISTS idx_tasks_session ON tasks(session_id);
                CREATE INDEX IF NOT EXISTS idx_events_workspace_time
                    ON events(workspace_id, occurred_at);
                CREATE INDEX IF NOT EXISTS idx_memory_workspace_scope_time
                    ON memory(workspace_id, scope, created_at);
                CREATE INDEX IF NOT EXISTS idx_workflows_workspace ON workflows(workspace_id);
                CREATE INDEX IF NOT EXISTS idx_agents_workspace ON agents(workspace_id);
                CREATE INDEX IF NOT EXISTS idx_agents_state_lease
                    ON agents(state, lease_expires_at);
                CREATE INDEX IF NOT EXISTS idx_agent_events_agent_sequence
                    ON agent_lifecycle_events(agent_id, sequence);
                """
            )

    def query(self, sql: str, params: tuple[Any, ...] = ()) -> list[sqlite3.Row]:
        statement = sql.lstrip()
        if not statement.upper().startswith("SELECT "):
            raise ValueError("StateStore.query is read-only and accepts SELECT statements only")
        with sqlite3.connect(self.path) as db:
            db.execute("PRAGMA foreign_keys=ON")
            db.row_factory = sqlite3.Row
            return list(db.execute(statement, params))

    def upsert_workspace(self, workspace_id: str, owner_user_id: str, created_at: str) -> None:
        with sqlite3.connect(self.path) as db:
            db.execute("PRAGMA foreign_keys=ON")
            db.execute(
                "INSERT INTO workspaces VALUES (?,?,?) "
                "ON CONFLICT(workspace_id) DO UPDATE SET owner_user_id=excluded.owner_user_id",
                (workspace_id, owner_user_id, created_at),
            )

    def upsert_session(self, row: tuple[str, str, str, str, str, str]) -> None:
        with sqlite3.connect(self.path) as db:
            db.execute("PRAGMA foreign_keys=ON")
            db.execute(
                "INSERT INTO sessions VALUES (?,?,?,?,?,?) "
                "ON CONFLICT(session_id) DO UPDATE SET state=excluded.state",
                row,
            )

    def upsert_task(self, row: tuple[str, str, str, str, str, str, str, str, str]) -> None:
        with sqlite3.connect(self.path) as db:
            db.execute("PRAGMA foreign_keys=ON")
            db.execute(
                "INSERT INTO tasks VALUES (?,?,?,?,?,?,?,?,?) "
                "ON CONFLICT(task_id) DO UPDATE SET "
                "state=excluded.state, dependencies=excluded.dependencies, "
                "platform_run_ids=excluded.platform_run_ids",
                row,
            )

    def append_event(
        self,
        row: tuple[
            str, str, str, str, str | None, str | None, str | None, str | None, str, str, str
        ],
    ) -> None:
        with sqlite3.connect(self.path) as db:
            db.execute("PRAGMA foreign_keys=ON")
            db.execute("INSERT INTO events VALUES (?,?,?,?,?,?,?,?,?,?,?)", row)

    def put_memory(self, row: tuple[str, str, str, str, str, str]) -> None:
        with sqlite3.connect(self.path) as db:
            db.execute("PRAGMA foreign_keys=ON")
            db.execute("INSERT INTO memory VALUES (?,?,?,?,?,?)", row)

    def put_workflow(self, row: tuple[str, str, str, str, str]) -> None:
        with sqlite3.connect(self.path) as db:
            db.execute("PRAGMA foreign_keys=ON")
            db.execute("INSERT INTO workflows VALUES (?,?,?,?,?)", row)

    def get_task(self, task_id: str) -> sqlite3.Row | None:
        rows = self.query(
            "SELECT task_id,workspace_id,session_id,agent_id,intent,state,dependencies,"
            "platform_run_ids,created_at FROM tasks WHERE task_id=?",
            (task_id,),
        )
        return rows[0] if rows else None

    def find_task_by_platform_run(self, run_id: str) -> sqlite3.Row | None:
        rows = self.query(
            "SELECT task_id,workspace_id,session_id,agent_id,intent,state,dependencies,"
            "platform_run_ids,created_at FROM tasks"
        )
        for row in rows:
            try:
                run_ids = json.loads(row["platform_run_ids"])
            except (TypeError, json.JSONDecodeError):
                continue
            if isinstance(run_ids, list) and run_id in run_ids:
                return row
        return None


    def register_agent(self, definition: Any, registered_at: str) -> None:
        values = (
            definition.agent_id,
            definition.workspace_id,
            definition.name,
            definition.version,
            definition.entrypoint,
            json.dumps(tuple(definition.capabilities), sort_keys=True),
            json.dumps(dict(definition.configuration), sort_keys=True),
            json.dumps(
                {
                    "enabled": definition.restart_policy.enabled,
                    "max_restarts": definition.restart_policy.max_restarts,
                    "backoff_seconds": definition.restart_policy.backoff_seconds,
                },
                sort_keys=True,
            ),
            json.dumps(
                {
                    "heartbeat_interval_seconds": definition.runtime.heartbeat_interval_seconds,
                    "heartbeat_timeout_seconds": definition.runtime.heartbeat_timeout_seconds,
                    "shutdown_timeout_seconds": definition.runtime.shutdown_timeout_seconds,
                },
                sort_keys=True,
            ),
            "registered",
            "unknown",
            0,
            0,
            None,
            None,
            registered_at,
            registered_at,
        )
        with sqlite3.connect(self.path) as db:
            db.execute("PRAGMA foreign_keys=ON")
            existing = db.execute(
                "SELECT version FROM agents WHERE agent_id=?", (definition.agent_id,)
            ).fetchone()
            if existing is not None and existing[0] != definition.version:
                raise ValueError("agent version is already bound to a different registered version")
            db.execute(
                "INSERT OR IGNORE INTO agents VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                values,
            )
            if existing is None:
                import hashlib
                event_id = hashlib.sha256(
                    f"agent:{definition.agent_id}:1:agent.registered".encode()
                ).hexdigest()
                db.execute(
                    "INSERT INTO agent_lifecycle_events VALUES (?,?,?,?,?,?,?,?,?,?)",
                    (
                        event_id,
                        definition.agent_id,
                        definition.workspace_id,
                        1,
                        "agent.registered",
                        None,
                        "registered",
                        registered_at,
                        event_id,
                        "{}",
                    ),
                )

    def get_agent(self, agent_id: str) -> sqlite3.Row | None:
        with sqlite3.connect(self.path) as db:
            db.row_factory = sqlite3.Row
            return db.execute("SELECT * FROM agents WHERE agent_id=?", (agent_id,)).fetchone()

    def transition_agent(
        self,
        agent_id: str,
        expected_state: str,
        new_state: str,
        occurred_at: str,
        event_type: str,
        payload: dict[str, object],
    ) -> None:
        with sqlite3.connect(self.path) as db:
            db.execute("PRAGMA foreign_keys=ON")
            db.execute("BEGIN IMMEDIATE")
            row = db.execute("SELECT * FROM agents WHERE agent_id=?", (agent_id,)).fetchone()
            if row is None:
                raise ValueError("agent is not registered")
            if row[9] != expected_state:
                raise RuntimeError(
                    f"agent state changed concurrently: expected {expected_state}, found {row[9]}"
                )
            sequence_row = db.execute(
                "SELECT COALESCE(MAX(sequence), 0) FROM agent_lifecycle_events WHERE agent_id=?",
                (agent_id,),
            ).fetchone()
            sequence = int(sequence_row[0]) + 1
            state_version = int(row[11]) + 1
            event_id = (
                __import__("hashlib")
                .sha256(f"agent:{agent_id}:{sequence}:{event_type}".encode())
                .hexdigest()
            )
            health = (
                "healthy"
                if new_state == "running"
                else "crashed"
                if new_state == "crashed"
                else "stopped"
                if new_state == "stopped"
                else row[10]
            )
            cursor = db.execute(
                "UPDATE agents SET state=?,health_state=?,state_version=?,updated_at=? "
                "WHERE agent_id=? AND state=? AND state_version=?",
                (
                    new_state,
                    health,
                    state_version,
                    occurred_at,
                    agent_id,
                    expected_state,
                    int(row[11]),
                ),
            )
            if cursor.rowcount != 1:
                raise RuntimeError("agent transition lost optimistic-concurrency race")
            db.execute(
                "INSERT INTO agent_lifecycle_events VALUES (?,?,?,?,?,?,?,?,?,?)",
                (
                    event_id,
                    agent_id,
                    row[1],
                    sequence,
                    event_type,
                    expected_state,
                    new_state,
                    occurred_at,
                    event_id,
                    json.dumps(payload, sort_keys=True),
                ),
            )
            db.commit()

    def record_agent_heartbeat(
        self, agent_id: str, heartbeat_at: str, lease_expires_at: str
    ) -> None:
        with sqlite3.connect(self.path) as db:
            cursor = db.execute(
                "UPDATE agents SET health_state='healthy',last_heartbeat_at=?,"
                "lease_expires_at=?,updated_at=? WHERE agent_id=? AND state='running'",
                (heartbeat_at, lease_expires_at, heartbeat_at, agent_id),
            )
            if cursor.rowcount != 1:
                raise ValueError("agent is not running")

    def increment_agent_restart(self, agent_id: str) -> None:
        from datetime import UTC, datetime

        with sqlite3.connect(self.path) as db:
            cursor = db.execute(
                "UPDATE agents SET restart_count=restart_count+1,updated_at=? WHERE agent_id=?",
                (datetime.now(UTC).isoformat(), agent_id),
            )
            if cursor.rowcount != 1:
                raise ValueError("agent is not registered")

    def running_agents(self) -> list[sqlite3.Row]:
        with sqlite3.connect(self.path) as db:
            db.row_factory = sqlite3.Row
            return list(db.execute("SELECT * FROM agents WHERE state='running'"))

    def agent_events(self, agent_id: str) -> list[sqlite3.Row]:
        with sqlite3.connect(self.path) as db:
            db.row_factory = sqlite3.Row
            return list(
                db.execute(
                    "SELECT * FROM agent_lifecycle_events WHERE agent_id=? ORDER BY sequence",
                    (agent_id,),
                )
            )
