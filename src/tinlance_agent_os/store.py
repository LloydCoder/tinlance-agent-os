"""Durable local Agent OS state store."""
from __future__ import annotations

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
            db.executescript(
                """
                CREATE TABLE IF NOT EXISTS workspaces (
                    workspace_id TEXT PRIMARY KEY,
                    owner_user_id TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS sessions (
                    session_id TEXT PRIMARY KEY,
                    workspace_id TEXT NOT NULL,
                    user_id TEXT NOT NULL,
                    agent_id TEXT NOT NULL,
                    state TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS tasks (
                    task_id TEXT PRIMARY KEY,
                    workspace_id TEXT NOT NULL,
                    session_id TEXT NOT NULL,
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
                    workspace_id TEXT NOT NULL,
                    session_id TEXT,
                    task_id TEXT,
                    agent_id TEXT,
                    platform_run_id TEXT,
                    correlation_id TEXT NOT NULL,
                    source TEXT NOT NULL,
                    payload TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS memory (
                    memory_id TEXT PRIMARY KEY,
                    workspace_id TEXT NOT NULL,
                    scope TEXT NOT NULL,
                    classification TEXT NOT NULL,
                    content TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS workflows (
                    workflow_id TEXT PRIMARY KEY,
                    workspace_id TEXT NOT NULL,
                    definition TEXT NOT NULL,
                    state TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
                """
            )

    def execute(self, sql: str, params: tuple[Any, ...] = ()) -> list[sqlite3.Row]:
        if not sql.lstrip().upper().startswith("SELECT "):
            raise ValueError("StateStore.execute is read-only")
        with sqlite3.connect(self.path) as db:
            db.row_factory = sqlite3.Row
            return list(db.execute(sql, params))

    def upsert_workspace(self, workspace_id: str, owner_user_id: str, created_at: str) -> None:
        with sqlite3.connect(self.path) as db:
            db.execute(
                "INSERT OR REPLACE INTO workspaces VALUES (?,?,?)",
                (workspace_id, owner_user_id, created_at),
            )

    def upsert_session(self, row: tuple[str, str, str, str, str, str]) -> None:
        with sqlite3.connect(self.path) as db:
            db.execute("INSERT OR REPLACE INTO sessions VALUES (?,?,?,?,?,?)", row)

    def upsert_task(self, row: tuple[str, str, str, str, str, str, str, str, str]) -> None:
        with sqlite3.connect(self.path) as db:
            db.execute("INSERT OR REPLACE INTO tasks VALUES (?,?,?,?,?,?,?,?,?)", row)

    def append_event(
        self,
        row: tuple[
            str,
            str,
            str,
            str,
            str | None,
            str | None,
            str | None,
            str | None,
            str,
            str,
            str,
        ],
    ) -> None:
        with sqlite3.connect(self.path) as db:
            db.execute("INSERT OR REPLACE INTO events VALUES (?,?,?,?,?,?,?,?,?,?,?)", row)

    def put_memory(self, row: tuple[str, str, str, str, str, str]) -> None:
        with sqlite3.connect(self.path) as db:
            db.execute("INSERT OR REPLACE INTO memory VALUES (?,?,?,?,?,?)", row)

    def put_workflow(self, row: tuple[str, str, str, str, str]) -> None:
        with sqlite3.connect(self.path) as db:
            db.execute("INSERT OR REPLACE INTO workflows VALUES (?,?,?,?,?)", row)
