"""Enterprise operator/control-center projection contracts.

M37 provides a durable, queryable operational projection for Agent OS. The
projection is deliberately non-authoritative: source runtimes remain the
systems of record and consequential operator actions must dispatch through
their existing governed boundaries.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Final

from .store import StateStore

_SCHEMA: Final = """
CREATE TABLE IF NOT EXISTS operator_entities (
    entity_type TEXT NOT NULL,
    entity_id TEXT NOT NULL,
    workspace_id TEXT NOT NULL,
    status TEXT NOT NULL,
    health TEXT NOT NULL,
    version TEXT,
    summary TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    generation INTEGER NOT NULL CHECK(generation >= 0),
    PRIMARY KEY(entity_type, entity_id)
);
CREATE INDEX IF NOT EXISTS idx_operator_entities_workspace
    ON operator_entities(workspace_id, entity_type, status);

CREATE TABLE IF NOT EXISTS operator_commands (
    command_id TEXT PRIMARY KEY,
    workspace_id TEXT NOT NULL,
    entity_type TEXT NOT NULL,
    entity_id TEXT NOT NULL,
    action TEXT NOT NULL,
    parameters_digest TEXT NOT NULL,
    state TEXT NOT NULL,
    created_at TEXT NOT NULL,
    generation INTEGER NOT NULL CHECK(generation >= 0)
);
"""


@dataclass(frozen=True, slots=True)
class OperatorEntity:
    entity_type: str
    entity_id: str
    workspace_id: str
    status: str
    health: str
    version: str | None = None
    summary: str = ""
    updated_at: datetime | None = None
    generation: int = 0


@dataclass(frozen=True, slots=True)
class OperatorCommand:
    command_id: str
    workspace_id: str
    entity_type: str
    entity_id: str
    action: str
    parameters_digest: str
    state: str = "requested"
    created_at: datetime | None = None
    generation: int = 0


class OperatorPlane:
    """Durable operational projection and command-intent surface."""

    def __init__(self, store: StateStore) -> None:
        self.store = store
        with sqlite3.connect(store.path) as db:
            db.executescript(_SCHEMA)

    @staticmethod
    def _timestamp(value: datetime | None) -> datetime:
        value = value or datetime.now(UTC)
        if value.tzinfo is None:
            raise ValueError("timestamp must be timezone-aware")
        return value.astimezone(UTC)

    def upsert_entity(self, entity: OperatorEntity) -> OperatorEntity:
        if not entity.entity_type or not entity.entity_id or not entity.workspace_id:
            raise ValueError("operator entity identity is required")
        if not entity.status or not entity.health:
            raise ValueError("operator entity status and health are required")
        if entity.generation < 0:
            raise ValueError("generation must be non-negative")
        updated_at = self._timestamp(entity.updated_at)
        normalized = OperatorEntity(
            entity.entity_type,
            entity.entity_id,
            entity.workspace_id,
            entity.status,
            entity.health,
            entity.version,
            entity.summary,
            updated_at,
            entity.generation,
        )
        with sqlite3.connect(self.store.path) as db:
            current = db.execute(
                """SELECT generation FROM operator_entities
                   WHERE entity_type=? AND entity_id=?""",
                (normalized.entity_type, normalized.entity_id),
            ).fetchone()
            generation = (
                normalized.generation
                if current is None
                else int(current[0]) + 1
            )
            db.execute(
                """INSERT INTO operator_entities
                (entity_type,entity_id,workspace_id,status,health,version,summary,
                 updated_at,generation)
                VALUES (?,?,?,?,?,?,?,?,?)
                ON CONFLICT(entity_type,entity_id) DO UPDATE SET
                  workspace_id=excluded.workspace_id,
                  status=excluded.status,
                  health=excluded.health,
                  version=excluded.version,
                  summary=excluded.summary,
                  updated_at=excluded.updated_at,
                  generation=excluded.generation""",
                (
                    normalized.entity_type,
                    normalized.entity_id,
                    normalized.workspace_id,
                    normalized.status,
                    normalized.health,
                    normalized.version,
                    normalized.summary,
                    normalized.updated_at.isoformat(),
                    generation,
                ),
            )
        return OperatorEntity(
            normalized.entity_type,
            normalized.entity_id,
            normalized.workspace_id,
            normalized.status,
            normalized.health,
            normalized.version,
            normalized.summary,
            normalized.updated_at,
            generation,
        )

    def list_entities(
        self,
        workspace_id: str,
        *,
        entity_type: str | None = None,
        status: str | None = None,
    ) -> list[OperatorEntity]:
        if not workspace_id:
            raise ValueError("workspace_id is required")
        clauses = ["workspace_id=?"]
        params: list[object] = [workspace_id]
        if entity_type is not None:
            clauses.append("entity_type=?")
            params.append(entity_type)
        if status is not None:
            clauses.append("status=?")
            params.append(status)
        query = (
            "SELECT entity_type,entity_id,workspace_id,status,health,version,"
            "summary,updated_at,generation FROM operator_entities WHERE "
            + " AND ".join(clauses)
            + " ORDER BY entity_type,entity_id"
        )
        with sqlite3.connect(self.store.path) as db:
            rows = db.execute(query, params).fetchall()
        return [
            OperatorEntity(
                str(row[0]),
                str(row[1]),
                str(row[2]),
                str(row[3]),
                str(row[4]),
                row[5],
                str(row[6]),
                datetime.fromisoformat(str(row[7])),
                int(row[8]),
            )
            for row in rows
        ]

    def request_command(self, command: OperatorCommand) -> OperatorCommand:
        if (
            not command.command_id
            or not command.workspace_id
            or not command.entity_type
            or not command.entity_id
            or not command.action
            or not command.parameters_digest
        ):
            raise ValueError("operator command identity is required")
        created_at = self._timestamp(command.created_at)
        normalized = OperatorCommand(
            command.command_id,
            command.workspace_id,
            command.entity_type,
            command.entity_id,
            command.action,
            command.parameters_digest,
            command.state,
            created_at,
            command.generation,
        )
        with sqlite3.connect(self.store.path) as db:
            db.execute(
                """INSERT INTO operator_commands
                (command_id,workspace_id,entity_type,entity_id,action,
                 parameters_digest,state,created_at,generation)
                VALUES (?,?,?,?,?,?,?,?,?)""",
                (
                    normalized.command_id,
                    normalized.workspace_id,
                    normalized.entity_type,
                    normalized.entity_id,
                    normalized.action,
                    normalized.parameters_digest,
                    normalized.state,
                    normalized.created_at.isoformat(),
                    normalized.generation,
                ),
            )
        return normalized
