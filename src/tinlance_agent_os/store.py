"""Durable local Agent OS state store with explicit query/write boundaries."""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast


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
                CREATE TABLE IF NOT EXISTS memory_records (
                    memory_id TEXT PRIMARY KEY,
                    workspace_id TEXT NOT NULL REFERENCES workspaces(workspace_id),
                    scope TEXT NOT NULL,
                    scope_id TEXT NOT NULL,
                    agent_id TEXT NOT NULL,
                    memory_key TEXT NOT NULL,
                    content TEXT NOT NULL,
                    classification TEXT NOT NULL,
                    trust TEXT NOT NULL,
                    state TEXT NOT NULL,
                    version INTEGER NOT NULL,
                    provenance TEXT NOT NULL,
                    content_digest TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    expires_at TEXT,
                    deleted_at TEXT,
                    quarantine_reason TEXT,
                    UNIQUE(workspace_id, scope, scope_id, memory_key, version)
                );
                CREATE INDEX IF NOT EXISTS idx_memory_records_scope
                    ON memory_records(workspace_id, scope, scope_id, updated_at);
                CREATE INDEX IF NOT EXISTS idx_memory_records_agent
                    ON memory_records(workspace_id, agent_id, state, updated_at);
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
                CREATE TABLE IF NOT EXISTS sdk_idempotency (
                    idempotency_key TEXT PRIMARY KEY,
                    operation TEXT NOT NULL,
                    subject_id TEXT NOT NULL,
                    state TEXT NOT NULL,
                    result_id TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_sdk_idempotency_subject
                    ON sdk_idempotency(operation, subject_id);
                CREATE TABLE IF NOT EXISTS agent_tasks (
                    task_id TEXT PRIMARY KEY,
                    workspace_id TEXT NOT NULL REFERENCES workspaces(workspace_id),
                    tenant_id TEXT NOT NULL,
                    owner_agent_id TEXT NOT NULL,
                    parent_task_id TEXT REFERENCES agent_tasks(task_id),
                    trace_id TEXT NOT NULL,
                    state TEXT NOT NULL,
                    delegated_capabilities TEXT NOT NULL,
                    intent TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS agent_message_sequences (
                    parent_task_id TEXT PRIMARY KEY REFERENCES agent_tasks(task_id),
                    next_sequence INTEGER NOT NULL
                );
                CREATE TABLE IF NOT EXISTS agent_messages (
                    message_id TEXT PRIMARY KEY,
                    workspace_id TEXT NOT NULL REFERENCES workspaces(workspace_id),
                    tenant_id TEXT NOT NULL,
                    sender_agent_id TEXT NOT NULL,
                    recipient_agent_id TEXT NOT NULL,
                    parent_task_id TEXT NOT NULL REFERENCES agent_tasks(task_id),
                    trace_id TEXT NOT NULL,
                    sequence INTEGER NOT NULL,
                    nonce TEXT NOT NULL,
                    payload TEXT NOT NULL,
                    payload_digest TEXT NOT NULL,
                    signature TEXT NOT NULL,
                    key_id TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    UNIQUE(parent_task_id, sequence)
                );
                CREATE INDEX IF NOT EXISTS idx_agent_tasks_parent
                    ON agent_tasks(parent_task_id, state);
                CREATE INDEX IF NOT EXISTS idx_agent_messages_recipient
                    ON agent_messages(recipient_agent_id, created_at);
                CREATE TABLE IF NOT EXISTS remote_endpoints (
                    endpoint_id TEXT PRIMARY KEY,
                    workspace_id TEXT NOT NULL REFERENCES workspaces(workspace_id),
                    tenant_id TEXT NOT NULL,
                    endpoint_fingerprint TEXT NOT NULL,
                    address TEXT NOT NULL,
                    protocol TEXT NOT NULL,
                    protocol_version TEXT NOT NULL,
                    state TEXT NOT NULL,
                    last_heartbeat TEXT NOT NULL,
                    enrolled_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    UNIQUE(workspace_id, endpoint_fingerprint)
                );
                CREATE TABLE IF NOT EXISTS remote_tasks (
                    task_id TEXT PRIMARY KEY,
                    workspace_id TEXT NOT NULL REFERENCES workspaces(workspace_id),
                    endpoint_id TEXT NOT NULL REFERENCES remote_endpoints(endpoint_id),
                    platform_task_id TEXT,
                    idempotency_key TEXT NOT NULL UNIQUE,
                    state TEXT NOT NULL,
                    trace_id TEXT NOT NULL,
                    assigned_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_remote_endpoints_health
                    ON remote_endpoints(workspace_id, state, last_heartbeat);
                CREATE INDEX IF NOT EXISTS idx_remote_tasks_endpoint
                    ON remote_tasks(endpoint_id, state, updated_at);
                CREATE TABLE IF NOT EXISTS channels (
                    channel_id TEXT PRIMARY KEY,
                    workspace_id TEXT NOT NULL REFERENCES workspaces(workspace_id),
                    kind TEXT NOT NULL,
                    endpoint_id TEXT NOT NULL,
                    state TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    UNIQUE(workspace_id, kind, endpoint_id)
                );
                CREATE TABLE IF NOT EXISTS channel_bindings (
                    channel_id TEXT PRIMARY KEY REFERENCES channels(channel_id),
                    workspace_id TEXT NOT NULL REFERENCES workspaces(workspace_id),
                    session_id TEXT REFERENCES sessions(session_id),
                    task_id TEXT REFERENCES tasks(task_id),
                    agent_id TEXT,
                    trace_id TEXT NOT NULL,
                    version INTEGER NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS channel_messages (
                    message_id TEXT PRIMARY KEY,
                    channel_id TEXT NOT NULL REFERENCES channels(channel_id),
                    workspace_id TEXT NOT NULL REFERENCES workspaces(workspace_id),
                    session_id TEXT,
                    task_id TEXT,
                    agent_id TEXT,
                    trace_id TEXT NOT NULL,
                    sequence INTEGER NOT NULL,
                    payload TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    UNIQUE(channel_id, sequence)
                );
                CREATE INDEX IF NOT EXISTS idx_channel_messages_context
                    ON channel_messages(workspace_id, session_id, task_id, created_at);
                CREATE TABLE IF NOT EXISTS workspace_resources (
                    workspace_id TEXT NOT NULL REFERENCES workspaces(workspace_id),
                    resource_type TEXT NOT NULL,
                    resource_id TEXT NOT NULL,
                    state TEXT NOT NULL,
                    metadata TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    PRIMARY KEY(workspace_id, resource_type, resource_id)
                );
                CREATE INDEX IF NOT EXISTS idx_channels_workspace
                    ON channels(workspace_id, state);
                CREATE INDEX IF NOT EXISTS idx_channel_bindings_workspace
                    ON channel_bindings(workspace_id, session_id, task_id);
                CREATE INDEX IF NOT EXISTS idx_workspace_resources
                    ON workspace_resources(workspace_id, resource_type, state);
                CREATE TABLE IF NOT EXISTS workflow_instances (
                    instance_id TEXT PRIMARY KEY,
                    workflow_id TEXT NOT NULL,
                    workspace_id TEXT NOT NULL REFERENCES workspaces(workspace_id),
                    state TEXT NOT NULL,
                    version INTEGER NOT NULL,
                    trigger_type TEXT NOT NULL,
                    trigger_id TEXT,
                    context TEXT NOT NULL,
                    checkpoint TEXT,
                    deadline_at TEXT,
                    cancel_requested INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS workflow_step_runs (
                    instance_id TEXT NOT NULL REFERENCES workflow_instances(instance_id),
                    step_id TEXT NOT NULL,
                    state TEXT NOT NULL,
                    attempt INTEGER NOT NULL,
                    next_attempt_at TEXT,
                    idempotency_key TEXT NOT NULL,
                    platform_run_id TEXT,
                    approval_id TEXT,
                    input_data TEXT NOT NULL,
                    output_data TEXT,
                    error TEXT,
                    started_at TEXT,
                    completed_at TEXT,
                    updated_at TEXT NOT NULL,
                    PRIMARY KEY(instance_id, step_id)
                );
                CREATE TABLE IF NOT EXISTS workflow_events (
                    event_id TEXT PRIMARY KEY,
                    instance_id TEXT NOT NULL REFERENCES workflow_instances(instance_id),
                    sequence INTEGER NOT NULL,
                    event_type TEXT NOT NULL,
                    step_id TEXT,
                    occurred_at TEXT NOT NULL,
                    payload TEXT NOT NULL,
                    UNIQUE(instance_id, sequence)
                );
                CREATE TABLE IF NOT EXISTS workflow_schedules (
                    schedule_id TEXT PRIMARY KEY,
                    workflow_id TEXT NOT NULL,
                    workspace_id TEXT NOT NULL REFERENCES workspaces(workspace_id),
                    cron TEXT NOT NULL,
                    enabled INTEGER NOT NULL,
                    next_run_at TEXT NOT NULL,
                    last_run_at TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_workflow_instances_workspace
                    ON workflow_instances(workspace_id, state, updated_at);
                CREATE INDEX IF NOT EXISTS idx_workflow_steps_retry
                    ON workflow_step_runs(state, next_attempt_at);
                CREATE INDEX IF NOT EXISTS idx_workflow_events_instance
                    ON workflow_events(instance_id, sequence);
                CREATE INDEX IF NOT EXISTS idx_workflow_schedules_due
                    ON workflow_schedules(enabled, next_run_at);
                CREATE TABLE IF NOT EXISTS scheduler_schedules (
                    schedule_id TEXT PRIMARY KEY,
                    workspace_id TEXT NOT NULL REFERENCES workspaces(workspace_id),
                    name TEXT NOT NULL,
                    kind TEXT NOT NULL,
                    expression TEXT NOT NULL,
                    timezone TEXT NOT NULL,
                    enabled INTEGER NOT NULL,
                    misfire_policy TEXT NOT NULL,
                    max_concurrency INTEGER NOT NULL,
                    next_run_at TEXT NOT NULL,
                    last_run_at TEXT,
                    generation INTEGER NOT NULL,
                    metadata TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    UNIQUE(workspace_id, name)
                );
                CREATE TABLE IF NOT EXISTS scheduler_jobs (
                    job_id TEXT PRIMARY KEY,
                    schedule_id TEXT NOT NULL REFERENCES scheduler_schedules(schedule_id),
                    workspace_id TEXT NOT NULL REFERENCES workspaces(workspace_id),
                    scheduled_for TEXT NOT NULL,
                    state TEXT NOT NULL,
                    attempt INTEGER NOT NULL,
                    lease_owner TEXT,
                    lease_expires_at TEXT,
                    started_at TEXT,
                    finished_at TEXT,
                    error TEXT,
                    payload TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    UNIQUE(schedule_id, scheduled_for)
                );
                CREATE INDEX IF NOT EXISTS idx_scheduler_schedules_due
                    ON scheduler_schedules(enabled, next_run_at);
                CREATE INDEX IF NOT EXISTS idx_scheduler_jobs_due
                    ON scheduler_jobs(workspace_id, state, scheduled_for);
                CREATE INDEX IF NOT EXISTS idx_scheduler_jobs_lease
                    ON scheduler_jobs(state, lease_expires_at);
                CREATE TABLE IF NOT EXISTS knowledge_sources (
                    source_id TEXT PRIMARY KEY,
                    workspace_id TEXT NOT NULL REFERENCES workspaces(workspace_id),
                    name TEXT NOT NULL,
                    authority_rank INTEGER NOT NULL,
                    freshness_seconds INTEGER NOT NULL,
                    metadata TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    UNIQUE(workspace_id, name)
                );
                CREATE TABLE IF NOT EXISTS knowledge_documents (
                    document_id TEXT PRIMARY KEY,
                    source_id TEXT NOT NULL REFERENCES knowledge_sources(source_id),
                    workspace_id TEXT NOT NULL REFERENCES workspaces(workspace_id),
                    uri TEXT NOT NULL,
                    title TEXT NOT NULL,
                    content TEXT NOT NULL,
                    content_digest TEXT NOT NULL,
                    source_version TEXT,
                    collected_at TEXT NOT NULL,
                    valid_from TEXT,
                    valid_until TEXT,
                    classification TEXT NOT NULL,
                    trust TEXT NOT NULL,
                    metadata TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    UNIQUE(workspace_id, uri, content_digest)
                );
                CREATE INDEX IF NOT EXISTS idx_knowledge_documents_source
                    ON knowledge_documents(workspace_id, source_id, collected_at);
                CREATE INDEX IF NOT EXISTS idx_knowledge_documents_validity
                    ON knowledge_documents(workspace_id, valid_from, valid_until);
                CREATE TABLE IF NOT EXISTS knowledge_chunks (
                    chunk_id TEXT PRIMARY KEY,
                    document_id TEXT NOT NULL REFERENCES knowledge_documents(document_id),
                    workspace_id TEXT NOT NULL REFERENCES workspaces(workspace_id),
                    ordinal INTEGER NOT NULL,
                    content TEXT NOT NULL,
                    content_digest TEXT NOT NULL,
                    metadata TEXT NOT NULL,
                    UNIQUE(document_id, ordinal)
                );
                CREATE INDEX IF NOT EXISTS idx_knowledge_chunks_document
                    ON knowledge_chunks(document_id, ordinal);
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

    def insert_memory_record(self, row: tuple[object, ...]) -> None:
        with sqlite3.connect(self.path) as db:
            db.execute("PRAGMA foreign_keys=ON")
            db.execute(
                "INSERT INTO memory_records VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                row,
            )
            db.commit()

    def get_memory_record(self, memory_id: str) -> sqlite3.Row | None:
        with sqlite3.connect(self.path) as db:
            db.row_factory = sqlite3.Row
            row = db.execute(
                "SELECT * FROM memory_records WHERE memory_id=?", (memory_id,)
            ).fetchone()
            return cast(sqlite3.Row | None, row)

    def memory_current(
        self, *, workspace_id: str, scope: str, scope_id: str, memory_key: str
    ) -> sqlite3.Row | None:
        with sqlite3.connect(self.path) as db:
            db.row_factory = sqlite3.Row
            row = db.execute(
                "SELECT * FROM memory_records "
                "WHERE workspace_id=? AND scope=? AND scope_id=? AND memory_key=? "
                "AND state != 'deleted' ORDER BY version DESC LIMIT 1",
                (workspace_id, scope, scope_id, memory_key),
            ).fetchone()
            return cast(sqlite3.Row | None, row)

    def search_memory_records(
        self,
        *,
        workspace_id: str,
        agent_id: str,
        scopes: tuple[str, ...],
        session_id: str | None,
        task_id: str | None,
        max_classification: int,
        include_quarantined: bool,
    ) -> list[sqlite3.Row]:
        if not scopes:
            return []
        placeholders = ",".join("?" for _ in scopes)
        states = ("active", "quarantined") if include_quarantined else ("active",)
        state_placeholders = ",".join("?" for _ in states)
        params: list[object] = [workspace_id, agent_id, *scopes, *states]
        rows = self.query(
            "SELECT * FROM memory_records WHERE workspace_id=? AND agent_id=? "
            f"AND scope IN ({placeholders}) AND state IN ({state_placeholders}) "
            "AND CAST(CASE classification WHEN 'public' THEN 0 "
            "WHEN 'internal' THEN 1 WHEN 'confidential' THEN 2 ELSE 3 END AS INTEGER) <= ? "
            "AND (expires_at IS NULL OR expires_at > datetime('now'))",
            (*params, max_classification),
        )
        current: dict[tuple[str, str, str], sqlite3.Row] = {}
        for row in rows:
            key = (row["scope"], row["scope_id"], row["memory_key"])
            if key not in current or int(row["version"]) > int(current[key]["version"]):
                current[key] = row
        return list(current.values())

    def expire_memory_record(self, memory_id: str, now: str) -> None:
        with sqlite3.connect(self.path) as db:
            db.execute(
                "UPDATE memory_records SET state='expired',updated_at=? "
                "WHERE memory_id=? AND state='active'",
                (now, memory_id),
            )
            db.commit()

    def expire_memories(self, now: str) -> None:
        with sqlite3.connect(self.path) as db:
            db.execute(
                "UPDATE memory_records SET state='expired',updated_at=? "
                "WHERE state='active' AND expires_at IS NOT NULL AND expires_at <= ?",
                (now, now),
            )
            db.commit()

    def delete_memory_record(self, memory_id: str, now: str) -> None:
        with sqlite3.connect(self.path) as db:
            db.execute(
                "UPDATE memory_records SET state='deleted',deleted_at=?,updated_at=? "
                "WHERE memory_id=? AND state IN ('active','quarantined','expired')",
                (now, now, memory_id),
            )
            db.commit()

    def quarantine_memory_record(self, memory_id: str, reason: str, now: str) -> None:
        with sqlite3.connect(self.path) as db:
            db.execute(
                "UPDATE memory_records SET state='quarantined',trust='quarantined',"
                "quarantine_reason=?,updated_at=? WHERE memory_id=? AND state='active'",
                (reason, now, memory_id),
            )
            db.commit()

    def put_workflow(self, row: tuple[str, str, str, str, str]) -> None:
        with sqlite3.connect(self.path) as db:
            db.execute("PRAGMA foreign_keys=ON")
            db.execute("INSERT INTO workflows VALUES (?,?,?,?,?)", row)

    def create_workflow_instance(
        self,
        *,
        instance_id: str,
        workflow_id: str,
        workspace_id: str,
        state: str,
        trigger_type: str,
        trigger_id: str | None,
        context: str,
        checkpoint: str | None,
        deadline_at: str | None,
        created_at: str,
    ) -> None:
        with sqlite3.connect(self.path) as db:
            db.execute("PRAGMA foreign_keys=ON")
            db.execute(
                "INSERT INTO workflow_instances VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (
                    instance_id,
                    workflow_id,
                    workspace_id,
                    state,
                    1,
                    trigger_type,
                    trigger_id,
                    context,
                    checkpoint,
                    deadline_at,
                    0,
                    created_at,
                    created_at,
                ),
            )
            db.commit()

    def get_workflow_instance(self, instance_id: str) -> sqlite3.Row | None:
        rows = self.query("SELECT * FROM workflow_instances WHERE instance_id=?", (instance_id,))
        return rows[0] if rows else None

    def update_workflow_instance(
        self,
        *,
        instance_id: str,
        expected_version: int,
        state: str,
        checkpoint: str | None,
        context: str,
        cancel_requested: bool,
        updated_at: str,
    ) -> None:
        with sqlite3.connect(self.path) as db:
            db.execute("PRAGMA foreign_keys=ON")
            db.execute("BEGIN IMMEDIATE")
            cur = db.execute(
                "UPDATE workflow_instances SET state=?,version=version+1,checkpoint=?,"
                "context=?,cancel_requested=?,updated_at=? "
                "WHERE instance_id=? AND version=?",
                (
                    state,
                    checkpoint,
                    context,
                    int(cancel_requested),
                    updated_at,
                    instance_id,
                    expected_version,
                ),
            )
            if cur.rowcount != 1:
                raise RuntimeError("workflow instance version conflict")
            db.commit()

    def upsert_workflow_step(
        self,
        *,
        instance_id: str,
        step_id: str,
        state: str,
        attempt: int,
        next_attempt_at: str | None,
        idempotency_key: str,
        platform_run_id: str | None,
        approval_id: str | None,
        input_data: str,
        output_data: str | None,
        error: str | None,
        started_at: str | None,
        completed_at: str | None,
        updated_at: str,
    ) -> None:
        with sqlite3.connect(self.path) as db:
            db.execute(
                "INSERT INTO workflow_step_runs VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?) "
                "ON CONFLICT(instance_id,step_id) DO UPDATE SET "
                "state=excluded.state,attempt=excluded.attempt,next_attempt_at=excluded.next_attempt_at,"
                "idempotency_key=excluded.idempotency_key,platform_run_id=excluded.platform_run_id,"
                "approval_id=excluded.approval_id,input_data=excluded.input_data,"
                "output_data=excluded.output_data,error=excluded.error,started_at=excluded.started_at,"
                "completed_at=excluded.completed_at,updated_at=excluded.updated_at",
                (
                    instance_id,
                    step_id,
                    state,
                    attempt,
                    next_attempt_at,
                    idempotency_key,
                    platform_run_id,
                    approval_id,
                    input_data,
                    output_data,
                    error,
                    started_at,
                    completed_at,
                    updated_at,
                ),
            )
            db.commit()

    def get_workflow_steps(self, instance_id: str) -> list[sqlite3.Row]:
        return self.query(
            "SELECT * FROM workflow_step_runs WHERE instance_id=? ORDER BY step_id",
            (instance_id,),
        )

    def append_workflow_event(
        self,
        *,
        event_id: str,
        instance_id: str,
        event_type: str,
        step_id: str | None,
        occurred_at: str,
        payload: str,
    ) -> None:
        with sqlite3.connect(self.path) as db:
            db.execute("PRAGMA foreign_keys=ON")
            db.execute("BEGIN IMMEDIATE")
            row = db.execute(
                "SELECT COALESCE(MAX(sequence),0) FROM workflow_events WHERE instance_id=?",
                (instance_id,),
            ).fetchone()
            sequence = int(row[0]) + 1
            db.execute(
                "INSERT INTO workflow_events VALUES (?,?,?,?,?,?,?)",
                (event_id, instance_id, sequence, event_type, step_id, occurred_at, payload),
            )
            db.commit()

    def workflow_events(self, instance_id: str) -> list[sqlite3.Row]:
        return self.query(
            "SELECT * FROM workflow_events WHERE instance_id=? ORDER BY sequence",
            (instance_id,),
        )

    def due_workflow_schedules(self, now: str) -> list[sqlite3.Row]:
        return self.query(
            "SELECT * FROM workflow_schedules WHERE enabled=1 AND next_run_at<=? "
            "ORDER BY next_run_at,schedule_id",
            (now,),
        )

    def put_workflow_schedule(
        self,
        schedule_id: str,
        workflow_id: str,
        workspace_id: str,
        cron: str,
        next_run_at: str,
        created_at: str,
    ) -> None:
        with sqlite3.connect(self.path) as db:
            db.execute(
                "INSERT INTO workflow_schedules VALUES (?,?,?,?,?,?,?,?,?)",
                (
                    schedule_id,
                    workflow_id,
                    workspace_id,
                    cron,
                    1,
                    next_run_at,
                    None,
                    created_at,
                    created_at,
                ),
            )
            db.commit()

    def advance_workflow_schedule(
        self, schedule_id: str, next_run_at: str, last_run_at: str
    ) -> None:
        with sqlite3.connect(self.path) as db:
            db.execute(
                "UPDATE workflow_schedules SET next_run_at=?,last_run_at=?,updated_at=? "
                "WHERE schedule_id=?",
                (next_run_at, last_run_at, last_run_at, schedule_id),
            )
            db.commit()

    def put_knowledge_source(self, row: tuple[Any, ...]) -> None:
        with sqlite3.connect(self.path) as db:
            db.execute("PRAGMA foreign_keys=ON")
            db.execute(
                "INSERT INTO knowledge_sources VALUES (?,?,?,?,?,?,?,?) "
                "ON CONFLICT(source_id) DO UPDATE SET name=excluded.name,"
                "authority_rank=excluded.authority_rank,freshness_seconds=excluded.freshness_seconds,"
                "metadata=excluded.metadata,updated_at=excluded.updated_at",
                row,
            )
            db.commit()

    def get_knowledge_source(self, source_id: str) -> sqlite3.Row | None:
        rows = self.query("SELECT * FROM knowledge_sources WHERE source_id=?", (source_id,))
        return rows[0] if rows else None

    def put_knowledge_document(self, row: tuple[Any, ...]) -> None:
        with sqlite3.connect(self.path) as db:
            db.execute("PRAGMA foreign_keys=ON")
            db.execute(
                "INSERT INTO knowledge_documents VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                row,
            )
            db.commit()

    def get_knowledge_document(self, document_id: str) -> sqlite3.Row | None:
        rows = self.query("SELECT * FROM knowledge_documents WHERE document_id=?", (document_id,))
        return rows[0] if rows else None

    def put_knowledge_chunk(self, row: tuple[Any, ...]) -> None:
        with sqlite3.connect(self.path) as db:
            db.execute("PRAGMA foreign_keys=ON")
            db.execute(
                "INSERT INTO knowledge_chunks VALUES (?,?,?,?,?,?,?) "
                "ON CONFLICT(document_id, ordinal) DO UPDATE SET content=excluded.content,"
                "content_digest=excluded.content_digest,metadata=excluded.metadata",
                row,
            )
            db.commit()

    def search_knowledge_chunks(
        self, workspace_id: str, terms: tuple[str, ...], limit: int
    ) -> list[sqlite3.Row]:
        if not terms:
            return []
        if limit < 1 or limit > 200:
            raise ValueError("knowledge search limit must be between 1 and 200")
        pattern = "%" + "%".join(terms) + "%"
        return self.query(
            "SELECT c.*,d.document_id,d.source_id,d.uri,d.title,d.collected_at,"
            "d.valid_from,d.valid_until,d.classification,d.trust,d.metadata AS document_metadata,"
            "s.authority_rank,s.freshness_seconds,s.name AS source_name "
            "FROM knowledge_chunks c JOIN knowledge_documents d ON d.document_id=c.document_id "
            "JOIN knowledge_sources s ON s.source_id=d.source_id "
            "WHERE c.workspace_id=? AND lower(c.content) LIKE lower(?) "
            "ORDER BY s.authority_rank DESC,d.collected_at DESC,c.ordinal LIMIT ?",
            (workspace_id, pattern, limit),
        )

    def put_scheduler_schedule(self, row: tuple[Any, ...]) -> None:
        with sqlite3.connect(self.path) as db:
            db.execute("PRAGMA foreign_keys=ON")
            db.execute(
                "INSERT INTO scheduler_schedules VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                row,
            )
            db.commit()

    def update_scheduler_schedule(
        self,
        schedule_id: str,
        *,
        expected_generation: int,
        enabled: bool,
        next_run_at: str,
        last_run_at: str | None,
        generation: int,
        expression: str,
        timezone: str,
        misfire_policy: str,
        max_concurrency: int,
        metadata: str,
        updated_at: str,
    ) -> None:
        with sqlite3.connect(self.path) as db:
            db.execute("PRAGMA foreign_keys=ON")
            db.execute("BEGIN IMMEDIATE")
            result = db.execute(
                "UPDATE scheduler_schedules SET enabled=?,next_run_at=?,last_run_at=?,"
                "generation=?,expression=?,timezone=?,misfire_policy=?,max_concurrency=?,"
                "metadata=?,updated_at=? WHERE schedule_id=? AND generation=?",
                (
                    int(enabled),
                    next_run_at,
                    last_run_at,
                    generation,
                    expression,
                    timezone,
                    misfire_policy,
                    max_concurrency,
                    metadata,
                    updated_at,
                    schedule_id,
                    expected_generation,
                ),
            )
            if result.rowcount != 1:
                raise ValueError("scheduler generation conflict")
            db.commit()

    def get_scheduler_schedule(self, schedule_id: str) -> sqlite3.Row | None:
        rows = self.query(
            "SELECT * FROM scheduler_schedules WHERE schedule_id=?",
            (schedule_id,),
        )
        return rows[0] if rows else None

    def due_scheduler_schedules(self, now: str) -> list[sqlite3.Row]:
        return self.query(
            "SELECT * FROM scheduler_schedules WHERE enabled=1 AND next_run_at<=? "
            "ORDER BY next_run_at,schedule_id",
            (now,),
        )

    def create_scheduler_job(
        self,
        *,
        job_id: str,
        schedule_id: str,
        workspace_id: str,
        scheduled_for: str,
        payload: str,
        created_at: str,
    ) -> bool:
        with sqlite3.connect(self.path) as db:
            db.execute("PRAGMA foreign_keys=ON")
            try:
                db.execute(
                    "INSERT INTO scheduler_jobs VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                    (
                        job_id,
                        schedule_id,
                        workspace_id,
                        scheduled_for,
                        "queued",
                        0,
                        None,
                        None,
                        None,
                        None,
                        None,
                        payload,
                        created_at,
                        created_at,
                    ),
                )
            except sqlite3.IntegrityError as exc:
                if "scheduler_jobs.schedule_id, scheduler_jobs.scheduled_for" not in str(exc):
                    raise
                return False
            db.commit()
            return True

    def get_scheduler_job(self, job_id: str) -> sqlite3.Row | None:
        rows = self.query("SELECT * FROM scheduler_jobs WHERE job_id=?", (job_id,))
        return rows[0] if rows else None

    def due_scheduler_jobs(self, now: str, limit: int = 100) -> list[sqlite3.Row]:
        if limit < 1 or limit > 1000:
            raise ValueError("scheduler job limit must be between 1 and 1000")
        return self.query(
            "SELECT * FROM scheduler_jobs WHERE state='queued' AND scheduled_for<=? "
            "ORDER BY scheduled_for,job_id LIMIT ?",
            (now, limit),
        )

    def lease_scheduler_job(self, job_id: str, owner: str, lease_expires_at: str, now: str) -> bool:
        with sqlite3.connect(self.path) as db:
            db.execute("PRAGMA foreign_keys=ON")
            db.execute("BEGIN IMMEDIATE")
            result = db.execute(
                "UPDATE scheduler_jobs SET state='running',attempt=attempt+1,"
                "lease_owner=?,lease_expires_at=?,started_at=COALESCE(started_at,?),"
                "updated_at=? WHERE job_id=? AND state='queued'",
                (owner, lease_expires_at, now, now, job_id),
            )
            db.commit()
            return result.rowcount == 1

    def finish_scheduler_job(
        self,
        job_id: str,
        *,
        state: str,
        error: str | None,
        finished_at: str | None,
        now: str,
    ) -> None:
        if state not in {"succeeded", "failed", "cancelled", "dead_letter"}:
            raise ValueError("invalid scheduler job terminal state")
        with sqlite3.connect(self.path) as db:
            db.execute(
                "UPDATE scheduler_jobs SET state=?,error=?,finished_at=?,"
                "lease_owner=NULL,lease_expires_at=NULL,updated_at=? WHERE job_id=?",
                (state, error, finished_at, now, job_id),
            )
            db.commit()

    def release_expired_scheduler_jobs(self, now: str) -> int:
        with sqlite3.connect(self.path) as db:
            result = db.execute(
                "UPDATE scheduler_jobs SET state='queued',lease_owner=NULL,"
                "lease_expires_at=NULL,updated_at=? "
                "WHERE state='running' AND lease_expires_at IS NOT NULL AND lease_expires_at<=?",
                (now, now),
            )
            db.commit()
            return result.rowcount

    def create_agent_task(self, task: Any, *, intent: str) -> None:
        from datetime import UTC, datetime

        now = datetime.now(UTC).isoformat()
        with sqlite3.connect(self.path) as db:
            db.execute("PRAGMA foreign_keys=ON")
            db.execute(
                "INSERT INTO agent_tasks VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                (
                    task.task_id,
                    task.workspace_id,
                    task.tenant_id,
                    task.owner_agent_id,
                    task.parent_task_id,
                    task.trace_id,
                    task.state.value,
                    json.dumps(sorted(task.delegated_capabilities)),
                    intent,
                    now,
                    now,
                ),
            )
            db.commit()

    def get_agent_task(self, task_id: str) -> sqlite3.Row | None:
        with sqlite3.connect(self.path) as db:
            db.row_factory = sqlite3.Row
            row = db.execute("SELECT * FROM agent_tasks WHERE task_id=?", (task_id,)).fetchone()
            return cast(sqlite3.Row | None, row)

    def next_agent_message_sequence(self, task_id: str) -> int:
        with sqlite3.connect(self.path) as db:
            db.execute("PRAGMA foreign_keys=ON")
            db.execute("BEGIN IMMEDIATE")
            db.execute(
                "INSERT OR IGNORE INTO agent_message_sequences VALUES (?,1)",
                (task_id,),
            )
            row = db.execute(
                "SELECT next_sequence FROM agent_message_sequences WHERE parent_task_id=?",
                (task_id,),
            ).fetchone()
            sequence = int(row[0])
            db.execute(
                "UPDATE agent_message_sequences SET next_sequence=? WHERE parent_task_id=?",
                (sequence + 1, task_id),
            )
            db.commit()
            return sequence

    def append_agent_message(self, message: Any) -> None:
        from datetime import UTC, datetime

        now = datetime.now(UTC).isoformat()
        with sqlite3.connect(self.path) as db:
            db.execute("PRAGMA foreign_keys=ON")
            db.execute(
                "INSERT INTO agent_messages VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (
                    message.message_id,
                    message.workspace_id,
                    message.tenant_id,
                    message.sender_agent_id,
                    message.recipient_agent_id,
                    message.parent_task_id,
                    message.trace_id,
                    message.sequence,
                    message.nonce,
                    json.dumps(message.payload, sort_keys=True),
                    message.payload_digest,
                    message.signature,
                    message.key_id,
                    now,
                ),
            )
            db.commit()

    def cancel_agent_task_tree(self, root_task_id: str, tenant_id: str) -> tuple[str, ...]:
        with sqlite3.connect(self.path) as db:
            db.execute("PRAGMA foreign_keys=ON")
            db.execute("BEGIN IMMEDIATE")
            rows = db.execute(
                "WITH RECURSIVE tree(task_id) AS ("
                "SELECT task_id FROM agent_tasks WHERE task_id=? AND tenant_id=? "
                "UNION ALL SELECT t.task_id FROM agent_tasks t JOIN tree p "
                "ON t.parent_task_id=p.task_id WHERE t.tenant_id=?"
                ") SELECT task_id FROM tree",
                (root_task_id, tenant_id, tenant_id),
            ).fetchall()
            ids = tuple(row[0] for row in rows)
            if ids:
                placeholders = ",".join("?" for _ in ids)
                db.execute(
                    "UPDATE agent_tasks SET state='cancelled',updated_at=datetime('now') "
                    f"WHERE task_id IN ({placeholders}) "
                    "AND state NOT IN ('completed','failed','cancelled')",
                    ids,
                )
            db.commit()
            return ids

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

    def claim_idempotency(
        self,
        *,
        idempotency_key: str,
        operation: str,
        subject_id: str,
        now: str,
    ) -> tuple[bool, str | None]:
        """Atomically claim an SDK operation or return its completed result."""
        with sqlite3.connect(self.path) as db:
            db.execute("PRAGMA foreign_keys=ON")
            db.execute("BEGIN IMMEDIATE")
            row = db.execute(
                "SELECT operation,subject_id,state,result_id FROM sdk_idempotency "
                "WHERE idempotency_key=?",
                (idempotency_key,),
            ).fetchone()
            if row is not None:
                if row[0] != operation or row[1] != subject_id:
                    raise ValueError("idempotency key is already bound to another operation")
                return row[2] != "claimed", row[3]
            db.execute(
                "INSERT INTO sdk_idempotency VALUES (?,?,?,?,?,?,?)",
                (idempotency_key, operation, subject_id, "claimed", None, now, now),
            )
            db.commit()
            return False, None

    def complete_idempotency(
        self,
        *,
        idempotency_key: str,
        result_id: str,
        now: str,
    ) -> None:
        with sqlite3.connect(self.path) as db:
            cursor = db.execute(
                "UPDATE sdk_idempotency SET state='completed',result_id=?,updated_at=? "
                "WHERE idempotency_key=? AND state='claimed'",
                (result_id, now, idempotency_key),
            )
            if cursor.rowcount != 1:
                raise ValueError("idempotency operation is not claimed")
            db.commit()

    def get_agent(self, agent_id: str) -> sqlite3.Row | None:
        with sqlite3.connect(self.path) as db:
            db.row_factory = sqlite3.Row
            row = db.execute("SELECT * FROM agents WHERE agent_id=?", (agent_id,)).fetchone()
            return cast(sqlite3.Row | None, row)

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

    def upsert_channel(
        self,
        row: tuple[str, str, str, str, str, str, str],
    ) -> None:
        with sqlite3.connect(self.path) as db:
            db.execute("PRAGMA foreign_keys=ON")
            db.execute(
                "INSERT INTO channels VALUES (?,?,?,?,?,?,?) "
                "ON CONFLICT(channel_id) DO UPDATE SET "
                "state=excluded.state, updated_at=excluded.updated_at",
                row,
            )

    def bind_channel(
        self,
        row: tuple[str, str, str | None, str | None, str | None, str, int, str],
    ) -> None:
        with sqlite3.connect(self.path) as db:
            db.execute("PRAGMA foreign_keys=ON")
            db.execute(
                "INSERT INTO channel_bindings VALUES (?,?,?,?,?,?,?,?) "
                "ON CONFLICT(channel_id) DO UPDATE SET "
                "session_id=excluded.session_id, task_id=excluded.task_id, "
                "agent_id=excluded.agent_id, trace_id=excluded.trace_id, "
                "version=excluded.version, updated_at=excluded.updated_at",
                row,
            )

    def upsert_workspace_resource(
        self,
        row: tuple[str, str, str, str, str, str],
    ) -> None:
        with sqlite3.connect(self.path) as db:
            db.execute("PRAGMA foreign_keys=ON")
            db.execute(
                "INSERT INTO workspace_resources VALUES (?,?,?,?,?,?) "
                "ON CONFLICT(workspace_id,resource_type,resource_id) DO UPDATE SET "
                "state=excluded.state, metadata=excluded.metadata, updated_at=excluded.updated_at",
                row,
            )

    def append_channel_message(
        self,
        row: tuple[
            str,
            str,
            str,
            str | None,
            str | None,
            str | None,
            str,
            int,
            str,
            str,
        ],
    ) -> None:
        with sqlite3.connect(self.path) as db:
            db.execute("PRAGMA foreign_keys=ON")
            db.execute(
                "INSERT INTO channel_messages VALUES (?,?,?,?,?,?,?,?,?,?)",
                row,
            )

    def upsert_remote_endpoint(
        self,
        row: tuple[str, str, str, str, str, str, str, str, str, str, str],
    ) -> None:
        with sqlite3.connect(self.path) as db:
            db.execute("PRAGMA foreign_keys=ON")
            db.execute(
                "INSERT INTO remote_endpoints VALUES (?,?,?,?,?,?,?,?,?,?,?) "
                "ON CONFLICT(endpoint_id) DO UPDATE SET "
                "address=excluded.address, protocol=excluded.protocol, "
                "protocol_version=excluded.protocol_version, state=excluded.state, "
                "last_heartbeat=excluded.last_heartbeat, updated_at=excluded.updated_at",
                row,
            )

    def upsert_remote_task(
        self,
        row: tuple[str, str, str, str | None, str, str, str, str, str],
    ) -> None:
        with sqlite3.connect(self.path) as db:
            db.execute("PRAGMA foreign_keys=ON")
            db.execute(
                "INSERT INTO remote_tasks VALUES (?,?,?,?,?,?,?,?,?) "
                "ON CONFLICT(task_id) DO UPDATE SET "
                "platform_task_id=excluded.platform_task_id, state=excluded.state, "
                "trace_id=excluded.trace_id, updated_at=excluded.updated_at",
                row,
            )
