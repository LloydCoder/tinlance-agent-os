"""Tenant-scoped durable OS event delivery.

This module owns OS lifecycle notifications only. Event payloads are untrusted;
the Agent Platform remains the sole authorization and execution authority.
Delivery is at-least-once. Consumers must be idempotent.
"""

from __future__ import annotations

import hashlib
import json
import random
import re
import sqlite3
from contextlib import contextmanager
from collections.abc import Callable, Iterator, Mapping
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from enum import StrEnum
from pathlib import Path
from types import MappingProxyType
from uuid import uuid4


_TRACE_ID = re.compile(r"^[0-9a-f]{32}$")
_MAX_EVENT_BYTES = 1_048_576


class EventRuntimeError(RuntimeError):
    pass


class DeliveryState(StrEnum):
    PENDING = "pending"
    DELIVERED = "delivered"
    DEAD_LETTER = "dead_letter"


@dataclass(frozen=True, slots=True)
class EventEnvelope:
    event_id: str
    tenant_id: str
    workspace_id: str
    event_type: str
    payload: Mapping[str, object]
    correlation_id: str
    occurred_at: str
    dedupe_key: str
    trace_id: str
    execution_id: str | None = None
    source: str = "urn:tinlance:agent-os"

    def __post_init__(self) -> None:
        encoded = json.dumps(
            dict(self.payload), sort_keys=True, separators=(",", ":"), allow_nan=False
        )
        object.__setattr__(self, "payload", _freeze_json(json.loads(encoded)))

    def as_payload(self) -> dict[str, object]:
        value: dict[str, object] = {
            "specversion": "1.0",
            "id": self.event_id,
            "source": self.source,
            "type": self.event_type,
            "time": self.occurred_at,
            "datacontenttype": "application/json",
            "tenantid": self.tenant_id,
            "workspaceid": self.workspace_id,
            "traceid": self.trace_id,
            "correlationid": self.correlation_id,
            "data": _thaw_json(self.payload),
        }
        if self.execution_id is not None:
            value["executionid"] = self.execution_id
        return value


@dataclass(frozen=True, slots=True)
class Subscription:
    subscription_id: str
    tenant_id: str
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
    lease_token: str | None = None
    lease_owner: str | None = None
    lease_expires_at: str | None = None


def _required(value: str, name: str) -> None:
    if not isinstance(value, str) or not value or value != value.strip():
        raise EventRuntimeError(f"{name} must be normalized and non-empty")


def _freeze_json(value: object) -> object:
    if isinstance(value, dict):
        return MappingProxyType({key: _freeze_json(item) for key, item in value.items()})
    if isinstance(value, list):
        return tuple(_freeze_json(item) for item in value)
    return value


def _thaw_json(value: object) -> object:
    if isinstance(value, Mapping):
        return {key: _thaw_json(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [_thaw_json(item) for item in value]
    return value


class EventSignalRuntime:
    """SQLite-backed tenant-isolated event log, delivery inbox and replay audit."""

    def __init__(
        self,
        path: Path,
        *,
        retry_base_seconds: float = 0.25,
        retry_max_seconds: float = 30.0,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        if retry_base_seconds < 0 or retry_max_seconds < retry_base_seconds:
            raise ValueError("invalid retry backoff bounds")
        self.path = path
        self.retry_base_seconds = retry_base_seconds
        self.retry_max_seconds = retry_max_seconds
        self._clock = clock or (lambda: datetime.now(UTC))
        self._ensure_schema()

    def publish(
        self,
        *,
        tenant_id: str,
        workspace_id: str,
        event_type: str,
        payload: Mapping[str, object],
        correlation_id: str,
        dedupe_key: str,
        trace_id: str | None = None,
        execution_id: str | None = None,
    ) -> EventEnvelope:
        for value, name in (
            (tenant_id, "tenant_id"),
            (workspace_id, "workspace_id"),
            (event_type, "event_type"),
            (correlation_id, "correlation_id"),
            (dedupe_key, "dedupe_key"),
        ):
            _required(value, name)
        trace_id = trace_id or uuid4().hex
        if not _TRACE_ID.fullmatch(trace_id) or set(trace_id) == {"0"}:
            raise EventRuntimeError("trace_id must be a valid non-zero W3C trace identifier")
        if execution_id is not None:
            _required(execution_id, "execution_id")
        if not isinstance(payload, Mapping):
            raise EventRuntimeError("event payload must be a JSON object")
        try:
            encoded = json.dumps(
                dict(payload), sort_keys=True, separators=(",", ":"), allow_nan=False
            )
        except (TypeError, ValueError) as exc:
            raise EventRuntimeError(
                "payload must contain only finite JSON-compatible values"
            ) from exc
        if len(encoded.encode("utf-8")) > _MAX_EVENT_BYTES:
            raise EventRuntimeError("event payload exceeds the 1 MiB limit")
        digest = hashlib.sha256(encoded.encode("utf-8")).hexdigest()
        event_id = hashlib.sha256(
            f"{tenant_id}:{workspace_id}:{event_type}:{dedupe_key}".encode()
        ).hexdigest()
        occurred_at = self._now().isoformat().replace("+00:00", "Z")
        with self._db() as db:
            db.execute("BEGIN IMMEDIATE")
            existing = db.execute(
                "SELECT event_id,event_type,payload_digest,correlation_id,trace_id,"
                "execution_id,occurred_at FROM os_events_p3 "
                "WHERE tenant_id=? AND workspace_id=? AND dedupe_key=?",
                (tenant_id, workspace_id, dedupe_key),
            ).fetchone()
            if existing is not None:
                if (
                    existing[1] != event_type
                    or existing[2] != digest
                    or existing[3] != correlation_id
                    or existing[5] != execution_id
                ):
                    raise EventRuntimeError("dedupe key reused for a conflicting event")
                return EventEnvelope(
                    str(existing[0]),
                    tenant_id,
                    workspace_id,
                    event_type,
                    json.loads(encoded),
                    correlation_id,
                    str(existing[6]),
                    dedupe_key,
                    str(existing[4]),
                    execution_id,
                )
            db.execute(
                "INSERT INTO os_events_p3 "
                "(event_id,tenant_id,workspace_id,event_type,payload,correlation_id,occurred_at,"
                "dedupe_key,trace_id,execution_id,payload_digest) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                (
                    event_id,
                    tenant_id,
                    workspace_id,
                    event_type,
                    encoded,
                    correlation_id,
                    occurred_at,
                    dedupe_key,
                    trace_id,
                    execution_id,
                    digest,
                ),
            )
            subscriptions = db.execute(
                "SELECT subscription_id,max_attempts FROM os_subscriptions_p3 "
                "WHERE tenant_id=? AND workspace_id=? AND (event_type=? OR event_type='*')",
                (tenant_id, workspace_id, event_type),
            ).fetchall()
            for subscription_id, max_attempts in subscriptions:
                db.execute(
                    "INSERT INTO os_event_deliveries_p3 "
                    "(event_id,subscription_id,attempt,state,max_attempts,next_attempt_at) "
                    "VALUES (?,?,0,?,?,?)",
                    (
                        event_id,
                        subscription_id,
                        DeliveryState.PENDING.value,
                        max_attempts,
                        occurred_at,
                    ),
                )
        return EventEnvelope(
            event_id,
            tenant_id,
            workspace_id,
            event_type,
            json.loads(encoded),
            correlation_id,
            occurred_at,
            dedupe_key,
            trace_id,
            execution_id,
        )

    def subscribe(
        self,
        *,
        tenant_id: str,
        workspace_id: str,
        event_type: str,
        consumer_id: str,
        max_attempts: int = 3,
    ) -> Subscription:
        for value, name in (
            (tenant_id, "tenant_id"),
            (workspace_id, "workspace_id"),
            (event_type, "event_type"),
            (consumer_id, "consumer_id"),
        ):
            _required(value, name)
        if max_attempts < 1 or max_attempts > 100:
            raise EventRuntimeError("max_attempts must be between 1 and 100")
        subscription_id = hashlib.sha256(
            f"{tenant_id}:{workspace_id}:{event_type}:{consumer_id}".encode()
        ).hexdigest()
        with self._db() as db:
            db.execute(
                "INSERT INTO os_subscriptions_p3 "
                "(subscription_id,tenant_id,workspace_id,event_type,consumer_id,max_attempts) "
                "VALUES (?,?,?,?,?,?) ON CONFLICT(subscription_id) DO UPDATE "
                "SET max_attempts=excluded.max_attempts",
                (subscription_id, tenant_id, workspace_id, event_type, consumer_id, max_attempts),
            )
        return Subscription(
            subscription_id, tenant_id, workspace_id, event_type, consumer_id, max_attempts
        )

    def pending(self, tenant_id: str, workspace_id: str, limit: int = 100) -> tuple[Delivery, ...]:
        _required(tenant_id, "tenant_id")
        _required(workspace_id, "workspace_id")
        if limit < 1 or limit > 1000:
            raise EventRuntimeError("limit must be between 1 and 1000")
        with self._db() as db:
            rows = db.execute(
                "SELECT d.event_id,d.subscription_id,d.attempt,d.state,d.lease_token,"
                "d.lease_owner,d.lease_expires_at FROM os_event_deliveries_p3 d "
                "JOIN os_events_p3 e ON e.event_id=d.event_id "
                "WHERE e.tenant_id=? AND e.workspace_id=? AND d.state=? "
                "ORDER BY e.occurred_at LIMIT ?",
                (tenant_id, workspace_id, DeliveryState.PENDING.value, limit),
            ).fetchall()
        return tuple(self._delivery(row) for row in rows)

    def claim_pending(
        self,
        *,
        tenant_id: str,
        workspace_id: str,
        worker_id: str,
        limit: int = 100,
        lease_seconds: int = 30,
    ) -> tuple[Delivery, ...]:
        for value, name in (
            (tenant_id, "tenant_id"),
            (workspace_id, "workspace_id"),
            (worker_id, "worker_id"),
        ):
            _required(value, name)
        if limit < 1 or limit > 1000 or lease_seconds < 1 or lease_seconds > 3600:
            raise EventRuntimeError("invalid claim limit or lease duration")
        now = self._now()
        now_text = now.isoformat().replace("+00:00", "Z")
        expires = (now + timedelta(seconds=lease_seconds)).isoformat().replace("+00:00", "Z")
        claimed: list[Delivery] = []
        with self._db() as db:
            db.execute("BEGIN IMMEDIATE")
            db.execute(
                "UPDATE os_event_deliveries_p3 SET lease_token=NULL,lease_owner=NULL,"
                "lease_expires_at=NULL WHERE state=? "
                "AND lease_expires_at IS NOT NULL AND lease_expires_at<=?",
                (DeliveryState.PENDING.value, now_text),
            )
            rows = db.execute(
                "SELECT d.event_id,d.subscription_id,d.attempt,d.state "
                "FROM os_event_deliveries_p3 d JOIN os_events_p3 e ON e.event_id=d.event_id "
                "WHERE e.tenant_id=? AND e.workspace_id=? AND d.state=? "
                "AND d.lease_token IS NULL AND d.next_attempt_at<=? "
                "ORDER BY e.occurred_at LIMIT ?",
                (tenant_id, workspace_id, DeliveryState.PENDING.value, now_text, limit),
            ).fetchall()
            for event_id, subscription_id, attempt, state in rows:
                token = uuid4().hex
                db.execute(
                    "UPDATE os_event_deliveries_p3 SET lease_token=?,lease_owner=?,"
                    "lease_expires_at=?,attempt=attempt+1 "
                    "WHERE event_id=? AND subscription_id=? AND lease_token IS NULL",
                    (token, worker_id, expires, event_id, subscription_id),
                )
                claimed.append(
                    Delivery(
                        str(event_id),
                        str(subscription_id),
                        int(attempt) + 1,
                        DeliveryState(state),
                        token,
                        worker_id,
                        expires,
                    )
                )
        return tuple(claimed)

    def acknowledge(
        self,
        *,
        tenant_id: str,
        event_id: str,
        subscription_id: str,
        worker_id: str,
        lease_token: str,
    ) -> None:
        for value, name in (
            (tenant_id, "tenant_id"),
            (event_id, "event_id"),
            (subscription_id, "subscription_id"),
            (worker_id, "worker_id"),
            (lease_token, "lease_token"),
        ):
            _required(value, name)
        now = self._now().isoformat().replace("+00:00", "Z")
        with self._db() as db:
            result = db.execute(
                "UPDATE os_event_deliveries_p3 SET state=?,lease_token=NULL,"
                "lease_owner=NULL,lease_expires_at=NULL WHERE event_id=? "
                "AND subscription_id=? AND state=? AND lease_token=? "
                "AND lease_owner=? AND lease_expires_at> ? "
                "AND event_id IN (SELECT event_id FROM os_events_p3 WHERE tenant_id=?)",
                (
                    DeliveryState.DELIVERED.value,
                    event_id,
                    subscription_id,
                    DeliveryState.PENDING.value,
                    lease_token,
                    worker_id,
                    now,
                    tenant_id,
                ),
            )
            if result.rowcount != 1:
                raise EventRuntimeError("delivery lease is stale, unauthorized, or not pending")

    def reject(
        self,
        *,
        tenant_id: str,
        event_id: str,
        subscription_id: str,
        worker_id: str,
        lease_token: str,
    ) -> DeliveryState:
        now = datetime.now(UTC)
        now_text = now.isoformat().replace("+00:00", "Z")
        with self._db() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute(
                "SELECT d.attempt,d.max_attempts,d.state FROM os_event_deliveries_p3 d "
                "JOIN os_events_p3 e ON e.event_id=d.event_id "
                "WHERE e.tenant_id=? AND d.event_id=? AND d.subscription_id=? "
                "AND d.lease_token=? AND d.lease_owner=? AND d.lease_expires_at>?",
                (tenant_id, event_id, subscription_id, lease_token, worker_id, now_text),
            ).fetchone()
            if row is None or row[2] != DeliveryState.PENDING.value:
                raise EventRuntimeError("delivery lease is stale, unauthorized, or not pending")
            attempt, max_attempts = int(row[0]), int(row[1])
            state = DeliveryState.DEAD_LETTER if attempt >= max_attempts else DeliveryState.PENDING
            delay = min(
                self.retry_base_seconds * (2 ** max(0, attempt - 1)), self.retry_max_seconds
            )
            delay = random.uniform(delay / 2, delay) if delay else 0
            next_attempt = (now + timedelta(seconds=delay)).isoformat().replace("+00:00", "Z")
            db.execute(
                "UPDATE os_event_deliveries_p3 SET state=?,next_attempt_at=?,lease_token=NULL,"
                "lease_owner=NULL,lease_expires_at=NULL WHERE event_id=? AND subscription_id=?",
                (state.value, next_attempt, event_id, subscription_id),
            )
            return state

    def replay(
        self,
        *,
        tenant_id: str,
        workspace_id: str,
        operator_id: str,
        reason: str,
        event_type: str = "*",
    ) -> int:
        for value, name in (
            (tenant_id, "tenant_id"),
            (workspace_id, "workspace_id"),
            (operator_id, "operator_id"),
            (reason, "reason"),
        ):
            _required(value, name)
        if len(reason) > 1000:
            raise EventRuntimeError("replay reason exceeds 1000 characters")
        now = datetime.now(UTC).isoformat().replace("+00:00", "Z")
        with self._db() as db:
            db.execute("BEGIN IMMEDIATE")
            if event_type == "*":
                result = db.execute(
                    "UPDATE os_event_deliveries_p3 SET state=?,attempt=0,next_attempt_at=?,"
                    "lease_token=NULL,lease_owner=NULL,lease_expires_at=NULL WHERE state=? "
                    "AND event_id IN (SELECT event_id FROM os_events_p3 "
                    "WHERE tenant_id=? AND workspace_id=?)",
                    (
                        DeliveryState.PENDING.value,
                        now,
                        DeliveryState.DEAD_LETTER.value,
                        tenant_id,
                        workspace_id,
                    ),
                )
            else:
                result = db.execute(
                    "UPDATE os_event_deliveries_p3 SET state=?,attempt=0,next_attempt_at=?,"
                    "lease_token=NULL,lease_owner=NULL,lease_expires_at=NULL WHERE state=? "
                    "AND event_id IN (SELECT event_id FROM os_events_p3 WHERE tenant_id=? "
                    "AND workspace_id=? AND event_type=?)",
                    (
                        DeliveryState.PENDING.value,
                        now,
                        DeliveryState.DEAD_LETTER.value,
                        tenant_id,
                        workspace_id,
                        event_type,
                    ),
                )
            count = int(result.rowcount)
            db.execute(
                "INSERT INTO os_event_replays_p3 "
                "(tenant_id,workspace_id,operator_id,reason,event_type,replayed_count,replayed_at) "
                "VALUES (?,?,?,?,?,?,?)",
                (tenant_id, workspace_id, operator_id, reason, event_type, count, now),
            )
            return count

    def _now(self) -> datetime:
        value = self._clock()
        if value.tzinfo is None or value.utcoffset() is None:
            raise EventRuntimeError("clock must return a timezone-aware datetime")
        return value.astimezone(UTC)

    @staticmethod
    def _delivery(row: tuple[object, ...]) -> Delivery:
        attempt = row[2]
        if not isinstance(attempt, int):
            raise EventRuntimeError("delivery attempt is not an integer")
        return Delivery(
            str(row[0]),
            str(row[1]),
            attempt,
            DeliveryState(str(row[3])),
            str(row[4]) if row[4] is not None else None,
            str(row[5]) if row[5] is not None else None,
            str(row[6]) if row[6] is not None else None,
        )

    def _ensure_schema(self) -> None:
        with self._db() as db:
            db.executescript(
                """
                CREATE TABLE IF NOT EXISTS os_events_p3 (
                    event_id TEXT PRIMARY KEY,
                    tenant_id TEXT NOT NULL,
                    workspace_id TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    payload TEXT NOT NULL,
                    correlation_id TEXT NOT NULL,
                    occurred_at TEXT NOT NULL,
                    dedupe_key TEXT NOT NULL,
                    trace_id TEXT NOT NULL,
                    execution_id TEXT,
                    payload_digest TEXT NOT NULL,
                    UNIQUE(tenant_id, workspace_id, dedupe_key)
                );
                CREATE TABLE IF NOT EXISTS os_subscriptions_p3 (
                    subscription_id TEXT PRIMARY KEY,
                    tenant_id TEXT NOT NULL,
                    workspace_id TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    consumer_id TEXT NOT NULL,
                    max_attempts INTEGER NOT NULL CHECK(max_attempts BETWEEN 1 AND 100),
                    UNIQUE(tenant_id, workspace_id, event_type, consumer_id)
                );
                CREATE TABLE IF NOT EXISTS os_event_deliveries_p3 (
                    event_id TEXT NOT NULL REFERENCES os_events_p3(event_id),
                    subscription_id TEXT NOT NULL REFERENCES os_subscriptions_p3(subscription_id),
                    attempt INTEGER NOT NULL CHECK(attempt >= 0),
                    state TEXT NOT NULL CHECK(state IN ('pending','delivered','dead_letter')),
                    max_attempts INTEGER NOT NULL CHECK(max_attempts BETWEEN 1 AND 100),
                    next_attempt_at TEXT NOT NULL,
                    lease_token TEXT,
                    lease_owner TEXT,
                    lease_expires_at TEXT,
                    PRIMARY KEY(event_id, subscription_id),
                    CHECK(
                        (lease_token IS NULL AND lease_owner IS NULL AND lease_expires_at IS NULL)
                        OR (
                            lease_token IS NOT NULL
                            AND lease_owner IS NOT NULL
                            AND lease_expires_at IS NOT NULL
                        )
                    )
                );
                CREATE INDEX IF NOT EXISTS idx_os_p3_delivery_pending
                    ON os_event_deliveries_p3(state,next_attempt_at,lease_expires_at);
                CREATE TABLE IF NOT EXISTS os_event_replays_p3 (
                    replay_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    tenant_id TEXT NOT NULL,
                    workspace_id TEXT NOT NULL,
                    operator_id TEXT NOT NULL,
                    reason TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    replayed_count INTEGER NOT NULL CHECK(replayed_count >= 0),
                    replayed_at TEXT NOT NULL
                );
                """
            )

    @contextmanager
    def _db(self) -> Iterator[sqlite3.Connection]:
        db = sqlite3.connect(self.path, timeout=10, isolation_level=None)
        try:
            db.execute("PRAGMA foreign_keys=ON")
            db.execute("PRAGMA busy_timeout=10000")
            db.execute("PRAGMA journal_mode=WAL")
            yield db
            if db.in_transaction:
                db.commit()
        except Exception:
            if db.in_transaction:
                db.rollback()
            raise
        finally:
            db.close()
