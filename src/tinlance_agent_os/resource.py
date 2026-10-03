"""Resource, usage and cost accounting for Agent OS.

This module records OS-observed resource consumption and attributable cost
metadata. It never grants, enforces, or substitutes for Agent Platform
budgets/quotas. Monetary values use integer micro-units to avoid floating-point
accounting drift.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Final

from .store import StateStore

_SCHEMA: Final = """
CREATE TABLE IF NOT EXISTS resource_usage (
    usage_id TEXT PRIMARY KEY,
    workspace_id TEXT NOT NULL,
    resource TEXT NOT NULL,
    quantity INTEGER NOT NULL CHECK(quantity >= 0),
    unit TEXT NOT NULL,
    cost_micros INTEGER CHECK(cost_micros IS NULL OR cost_micros >= 0),
    agent_id TEXT,
    task_id TEXT,
    workflow_id TEXT,
    model TEXT,
    provider TEXT,
    occurred_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_resource_usage_workspace_time
    ON resource_usage(workspace_id, occurred_at);
CREATE INDEX IF NOT EXISTS idx_resource_usage_workspace_resource
    ON resource_usage(workspace_id, resource, occurred_at);
"""


@dataclass(frozen=True, slots=True)
class UsageRecord:
    usage_id: str
    workspace_id: str
    resource: str
    quantity: int
    unit: str
    cost_micros: int | None = None
    agent_id: str | None = None
    task_id: str | None = None
    workflow_id: str | None = None
    model: str | None = None
    provider: str | None = None
    occurred_at: datetime | None = None


@dataclass(frozen=True, slots=True)
class UsageSummary:
    workspace_id: str
    resource: str
    quantity: int
    cost_micros: int
    unit: str


class ResourceLedger:
    """Durable OS usage accounting, deliberately separate from Platform authority."""

    def __init__(self, store: StateStore) -> None:
        self.store = store
        with sqlite3.connect(store.path) as db:
            db.executescript(_SCHEMA)

    def record(self, record: UsageRecord) -> UsageRecord:
        if not record.workspace_id:
            raise ValueError("workspace_id is required")
        if not record.resource:
            raise ValueError("resource is required")
        if record.quantity < 0:
            raise ValueError("quantity must be non-negative")
        if record.cost_micros is not None and record.cost_micros < 0:
            raise ValueError("cost_micros must be non-negative")
        occurred_at: datetime = record.occurred_at or datetime.now(UTC)
        if occurred_at.tzinfo is None:
            raise ValueError("occurred_at must be timezone-aware")
        normalized = UsageRecord(
            usage_id=record.usage_id,
            workspace_id=record.workspace_id,
            resource=record.resource,
            quantity=record.quantity,
            unit=record.unit,
            cost_micros=record.cost_micros,
            agent_id=record.agent_id,
            task_id=record.task_id,
            workflow_id=record.workflow_id,
            model=record.model,
            provider=record.provider,
            occurred_at=occurred_at.astimezone(UTC),
        )
        with sqlite3.connect(self.store.path) as db:
            db.execute(
                """INSERT INTO resource_usage
                (usage_id,workspace_id,resource,quantity,unit,cost_micros,
                 agent_id,task_id,workflow_id,model,provider,occurred_at)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    normalized.usage_id,
                    normalized.workspace_id,
                    normalized.resource,
                    normalized.quantity,
                    normalized.unit,
                    normalized.cost_micros,
                    normalized.agent_id,
                    normalized.task_id,
                    normalized.workflow_id,
                    normalized.model,
                    normalized.provider,
                    occurred_at.astimezone(UTC).isoformat(),
                ),
            )
        return normalized

    def summarize(
        self,
        workspace_id: str,
        *,
        resource: str | None = None,
    ) -> list[UsageSummary]:
        query = (
            "SELECT resource, SUM(quantity), SUM(COALESCE(cost_micros,0)), "
            "MIN(unit) FROM resource_usage WHERE workspace_id=?"
        )
        params: list[object] = [workspace_id]
        if resource is not None:
            query += " AND resource=?"
            params.append(resource)
        query += " GROUP BY resource ORDER BY resource"
        with sqlite3.connect(self.store.path) as db:
            rows = db.execute(query, params).fetchall()
        return [
            UsageSummary(
                workspace_id,
                str(row[0]),
                int(row[1]),
                int(row[2]),
                str(row[3]),
            )
            for row in rows
        ]

    def attributable_cost_micros(
        self,
        workspace_id: str,
        *,
        agent_id: str | None = None,
        task_id: str | None = None,
        workflow_id: str | None = None,
    ) -> int:
        clauses = ["workspace_id=?"]
        params: list[object] = [workspace_id]
        for column, value in (
            ("agent_id", agent_id),
            ("task_id", task_id),
            ("workflow_id", workflow_id),
        ):
            if value is not None:
                clauses.append(f"{column}=?")
                params.append(value)
        with sqlite3.connect(self.store.path) as db:
            row = db.execute(
                "SELECT COALESCE(SUM(cost_micros),0) FROM resource_usage WHERE "
                + " AND ".join(clauses),
                params,
            ).fetchone()
        return int(row[0] if row else 0)
