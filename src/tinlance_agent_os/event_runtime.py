"""M28 durable event, signal and reactive runtime."""

from __future__ import annotations

import hashlib
import json
import sqlite3
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path


class EventRuntimeError(RuntimeError):
    pass


class DeliveryState(StrEnum):
    PENDING = "pending"
    DELIVERED = "delivered"
    DEAD_LETTER = "dead_letter"


@dataclass(frozen=True, slots=True)
class EventEnvelope:
    event_id: str
    workspace_id: str
    event_type: str
    payload: Mapping[str, object]
    correlation_id: str
    occurred_at: str
    dedupe_key: str


@dataclass(frozen=True, slots=True)
class Subscription:
    subscription_id: str
    workspace_id: str
    event_type: str
    consumer_id: str
    max_attempts: int = 3


@dataclass(frozen=True, slots=True)
class Delivery:
    event_id: str
    subscription_id: str
    attempt: int
    state: DeliveryState


class EventSignalRuntime:
    """Durable pub/sub and signal routing; handlers remain outside authority."""

    def __init__(self, path: Path) -> None:
        self.path = path
        self._ensure_schema()

    def publish(
        self,
        *,
        workspace_id: str,
        event_type: str,
        payload: Mapping[str, object],
        correlation_id: str,
        dedupe_key: str,
    ) -> EventEnvelope:
        for value, name in (
            (workspace_id, "workspace_id"),
            (event_type, "event_type"),
            (correlation_id, "correlation_id"),
            (dedupe_key, "dedupe_key"),
        ):
            if not value.strip():
                raise EventRuntimeError(f"{name} is required")
        encoded = json.dumps(dict(payload), sort_keys=True)
        event_id = hashlib.sha256(
            f"{workspace_id}:{event_type}:{correlation_id}:{dedupe_key}:{encoded}".encode()
        ).hexdigest()
        occurred_at = datetime.now(UTC).isoformat()
        with self._db() as db:
            existing = db.execute(
                "SELECT event_id FROM os_events WHERE workspace_id=? AND dedupe_key=?",
                (workspace_id, dedupe_key),
            ).fetchone()
            if existing is not None:
                event_id = str(existing[0])
                row = db.execute(
                    "SELECT event_id,workspace_id,event_type,payload,correlation_id,occurred_at,dedupe_key "
                    "FROM os_events WHERE event_id=?",
                    (event_id,),
                ).fetchone()
                return EventEnvelope(
                    row[0], row[1], row[2], json.loads(row[3]), row[4], row[5], row[6]
                )
            db.execute(
                "INSERT INTO os_events VALUES (?,?,?,?,?,?,?)",
                (event_id, workspace_id, event_type, encoded, correlation_id, occurred_at, dedupe_key),
            )
            subscriptions = db.execute(
                "SELECT subscription_id,max_attempts FROM os_subscriptions "
                "WHERE workspace_id=? AND (event_type=? OR event_type='*')",
                (workspace_id, event_type),
            ).fetchall()
            for subscription_id, max_attempts in subscriptions:
                db.execute(
                    "INSERT INTO os_event_deliveries VALUES (?,?,?,?,?)",
                    (event_id, subscription_id, 0, DeliveryState.PENDING.value, max_attempts),
                )
        return EventEnvelope(
            event_id, workspace_id, event_type, dict(payload), correlation_id, occurred_at, dedupe_key
        )

    def subscribe(
        self,
        *,
        workspace_id: str,
        event_type: str,
        consumer_id: str,
        max_attempts: int = 3,
    ) -> Subscription:
        if max_attempts < 1:
            raise EventRuntimeError("max_attempts must be >= 1")
        if not event_type.strip() or not consumer_id.strip():
            raise EventRuntimeError("event_type and consumer_id are required")
        subscription_id = hashlib.sha256(
            f"{workspace_id}:{event_type}:{consumer_id}".encode()
        ).hexdigest()
        with self._db() as db:
            db.execute(
                "INSERT INTO os_subscriptions VALUES (?,?,?,?,?) "
                "ON CONFLICT(subscription_id) DO UPDATE SET max_attempts=excluded.max_attempts",
                (subscription_id, workspace_id, event_type, consumer_id, max_attempts),
            )
        return Subscription(subscription_id, workspace_id, event_type, consumer_id, max_attempts)

    def pending(self, workspace_id: str, limit: int = 100) -> tuple[Delivery, ...]:
        if limit < 1:
            raise EventRuntimeError("limit must be >= 1")
        with self._db() as db:
            rows = db.execute(
                "SELECT d.event_id,d.subscription_id,d.attempt,d.state "
                "FROM os_event_deliveries d JOIN os_events e ON e.event_id=d.event_id "
                "WHERE e.workspace_id=? AND d.state=? ORDER BY e.occurred_at LIMIT ?",
                (workspace_id, DeliveryState.PENDING.value, limit),
            ).fetchall()
        return tuple(Delivery(row[0], row[1], int(row[2]), DeliveryState(row[3])) for row in rows)

    def acknowledge(self, event_id: str, subscription_id: str) -> None:
        with self._db() as db:
            updated = db.execute(
                "UPDATE os_event_deliveries SET state=?,attempt=attempt+1 "
                "WHERE event_id=? AND subscription_id=? AND state=?",
                (
                    DeliveryState.DELIVERED.value,
                    event_id,
                    subscription_id,
                    DeliveryState.PENDING.value,
                ),
            )
            if updated.rowcount != 1:
                raise EventRuntimeError("delivery is not pending")

    def reject(self, event_id: str, subscription_id: str) -> DeliveryState:
        with self._db() as db:
            row = db.execute(
                "SELECT attempt,max_attempts,state FROM os_event_deliveries "
                "WHERE event_id=? AND subscription_id=?",
                (event_id, subscription_id),
            ).fetchone()
            if row is None:
                raise EventRuntimeError("delivery does not exist")
            if row[2] != DeliveryState.PENDING.value:
                raise EventRuntimeError("delivery is not pending")
            attempt = int(row[0]) + 1
            state = (
                DeliveryState.DEAD_LETTER
                if attempt >= int(row[1])
                else DeliveryState.PENDING
            )
            db.execute(
                "UPDATE os_event_deliveries SET attempt=?,state=? "
                "WHERE event_id=? AND subscription_id=?",
                (attempt, state.value, event_id, subscription_id),
            )
            return state

    def replay(self, workspace_id: str, event_type: str = "*") -> int:
        with self._db() as db:
            if event_type == "*":
                result = db.execute(
                    "UPDATE os_event_deliveries SET state=? WHERE state=? "
                    "AND event_id IN (SELECT event_id FROM os_events WHERE workspace_id=?)",
                    (DeliveryState.PENDING.value, DeliveryState.DEAD_LETTER.value, workspace_id),
                )
            else:
                result = db.execute(
                    "UPDATE os_event_deliveries SET state=? WHERE state=? "
                    "AND event_id IN (SELECT event_id FROM os_events WHERE workspace_id=? AND event_type=?)",
                    (
                        DeliveryState.PENDING.value,
                        DeliveryState.DEAD_LETTER.value,
                        workspace_id,
                        event_type,
                    ),
                )
            return int(result.rowcount)

    def _ensure_schema(self) -> None:
        with self._db() as db:
            db.executescript(
                """
                CREATE TABLE IF NOT EXISTS os_events (
                    event_id TEXT PRIMARY KEY,
                    workspace_id TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    payload TEXT NOT NULL,
                    correlation_id TEXT NOT NULL,
                    occurred_at TEXT NOT NULL,
                    dedupe_key TEXT NOT NULL,
                    UNIQUE(workspace_id, dedupe_key)
                );
                CREATE TABLE IF NOT EXISTS os_subscriptions (
                    subscription_id TEXT PRIMARY KEY,
                    workspace_id TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    consumer_id TEXT NOT NULL,
                    max_attempts INTEGER NOT NULL,
                    UNIQUE(workspace_id, event_type, consumer_id)
                );
                CREATE TABLE IF NOT EXISTS os_event_deliveries (
                    event_id TEXT NOT NULL REFERENCES os_events(event_id),
                    subscription_id TEXT NOT NULL REFERENCES os_subscriptions(subscription_id),
                    attempt INTEGER NOT NULL,
                    state TEXT NOT NULL,
                    max_attempts INTEGER NOT NULL,
                    PRIMARY KEY(event_id, subscription_id)
                );
                CREATE INDEX IF NOT EXISTS idx_os_event_delivery_pending
                    ON os_event_deliveries(state, event_id);
                """
            )

    def _db(self) -> sqlite3.Connection:
        db = sqlite3.connect(self.path)
        db.execute("PRAGMA foreign_keys=ON")
        return db
