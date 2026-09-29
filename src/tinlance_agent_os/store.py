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
                CREATE INDEX IF NOT EXISTS idx_sessions_workspace ON sessions(workspace_id);
                CREATE INDEX IF NOT EXISTS idx_tasks_workspace ON tasks(workspace_id);
                CREATE INDEX IF NOT EXISTS idx_tasks_session ON tasks(session_id);
                CREATE INDEX IF NOT EXISTS idx_events_workspace_time
                    ON events(workspace_id, occurred_at);
                CREATE INDEX IF NOT EXISTS idx_memory_workspace_scope_time
                    ON memory(workspace_id, scope, created_at);
                CREATE INDEX IF NOT EXISTS idx_workflows_workspace ON workflows(workspace_id);
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
