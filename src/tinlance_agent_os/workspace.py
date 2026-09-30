"""Unified Agent OS workspace and channel runtime."""

from __future__ import annotations

import json
import secrets
import sqlite3
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from typing import Protocol

from .store import StateStore


def utc_now() -> datetime:
    return datetime.now(UTC)


class ChannelKind(StrEnum):
    WEB = "web"
    CLI = "cli"
    DESKTOP = "desktop"
    API = "api"
    MESSAGING = "messaging"
    NOTIFICATIONS = "notifications"


class ChannelState(StrEnum):
    ACTIVE = "active"
    PAUSED = "paused"
    DRAINING = "draining"
    CLOSED = "closed"


class WorkspaceError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class ChannelContext:
    channel_id: str
    workspace_id: str
    kind: ChannelKind
    endpoint_id: str
    session_id: str | None
    task_id: str | None
    agent_id: str | None
    trace_id: str
    version: int


@dataclass(frozen=True, slots=True)
class ChannelEnvelope:
    message_id: str
    channel_id: str
    workspace_id: str
    session_id: str | None
    task_id: str | None
    agent_id: str | None
    trace_id: str
    payload: Mapping[str, object]
    sequence: int


@dataclass(frozen=True, slots=True)
class WorkspaceSnapshot:
    workspace_id: str
    agents: tuple[str, ...]
    applications: tuple[str, ...]
    skills: tuple[str, ...]
    sessions: tuple[str, ...]
    tasks: tuple[str, ...]
    workflows: tuple[str, ...]
    memory: tuple[str, ...]
    integrations: tuple[str, ...]
    events: tuple[str, ...]
    channels: tuple[str, ...]


class ChannelAdapter(Protocol):
    kind: ChannelKind

    def endpoint_id(self) -> str: ...

    def send(self, envelope: ChannelEnvelope) -> None: ...


@dataclass(slots=True)
class DurableChannelAdapter:
    kind: ChannelKind
    runtime: ChannelRuntime
    context: ChannelContext

    def endpoint_id(self) -> str:
        return self.context.endpoint_id

    def send(self, envelope: ChannelEnvelope) -> None:
        self.runtime.emit(envelope)


class WebChannel(DurableChannelAdapter):
    kind = ChannelKind.WEB


class CLIChannel(DurableChannelAdapter):
    kind = ChannelKind.CLI


class DesktopChannel(DurableChannelAdapter):
    kind = ChannelKind.DESKTOP


class APIChannel(DurableChannelAdapter):
    kind = ChannelKind.API


class MessagingChannel(DurableChannelAdapter):
    kind = ChannelKind.MESSAGING


class NotificationChannel(DurableChannelAdapter):
    kind = ChannelKind.NOTIFICATIONS


class ChannelRuntime:
    """Maps presentation channels onto one durable OS lifecycle identity."""

    def __init__(self, store: StateStore) -> None:
        self.store = store

    def register(
        self,
        *,
        workspace_id: str,
        kind: ChannelKind,
        endpoint_id: str,
        channel_id: str | None = None,
    ) -> ChannelContext:
        if not endpoint_id.strip():
            raise WorkspaceError("channel endpoint is required")
        if not self._workspace_exists(workspace_id):
            raise WorkspaceError("workspace does not exist")
        channel_id = channel_id or f"ch_{secrets.token_hex(12)}"
        now = utc_now().isoformat()
        self.store.upsert_channel(
            (
                channel_id,
                workspace_id,
                kind.value,
                endpoint_id,
                ChannelState.ACTIVE.value,
                now,
                now,
            )
        )
        return ChannelContext(
            channel_id=channel_id,
            workspace_id=workspace_id,
            kind=kind,
            endpoint_id=endpoint_id,
            session_id=None,
            task_id=None,
            agent_id=None,
            trace_id=f"tr_{secrets.token_hex(12)}",
            version=0,
        )

    def bind(
        self,
        context: ChannelContext,
        *,
        session_id: str | None = None,
        task_id: str | None = None,
        agent_id: str | None = None,
        trace_id: str | None = None,
    ) -> ChannelContext:
        current = self._channel(context.channel_id)
        if current is None:
            raise WorkspaceError("channel does not exist")
        if current["workspace_id"] != context.workspace_id:
            raise WorkspaceError("channel workspace mismatch")

        session = self._session(session_id) if session_id else None
        task = self._task(task_id) if task_id else None
        if session_id and session is None:
            raise WorkspaceError("session does not exist")
        if task_id and task is None:
            raise WorkspaceError("task does not exist")

        if session is not None:
            self._require_workspace(session["workspace_id"], context.workspace_id)
            if agent_id is not None and session["agent_id"] != agent_id:
                raise WorkspaceError("agent/session identity mismatch")
            agent_id = str(session["agent_id"])

        if task is not None:
            self._require_workspace(task["workspace_id"], context.workspace_id)
            if session_id is not None and task["session_id"] != session_id:
                raise WorkspaceError("task/session identity mismatch")
            if agent_id is not None and task["agent_id"] != agent_id:
                raise WorkspaceError("agent/task identity mismatch")
            agent_id = str(task["agent_id"])
            session_id = str(task["session_id"])

        bound_trace = trace_id or context.trace_id
        if not bound_trace.strip():
            raise WorkspaceError("trace identity is required")

        version = context.version + 1
        now = utc_now().isoformat()
        self.store.bind_channel(
            (
                context.channel_id,
                context.workspace_id,
                session_id,
                task_id,
                agent_id,
                bound_trace,
                version,
                now,
            )
        )
        return ChannelContext(
            channel_id=context.channel_id,
            workspace_id=context.workspace_id,
            kind=context.kind,
            endpoint_id=context.endpoint_id,
            session_id=session_id,
            task_id=task_id,
            agent_id=agent_id,
            trace_id=bound_trace,
            version=version,
        )

    def handoff(
        self,
        source: ChannelContext,
        target: ChannelContext,
    ) -> ChannelContext:
        if source.workspace_id != target.workspace_id:
            raise WorkspaceError("cross-workspace channel handoff denied")
        if source.session_id != target.session_id or source.task_id != target.task_id:
            raise WorkspaceError("handoff must preserve session and task identity")
        if source.agent_id != target.agent_id:
            raise WorkspaceError("handoff must preserve agent identity")
        if source.trace_id != target.trace_id:
            raise WorkspaceError("handoff must preserve trace continuity")
        return self.bind(
            target,
            session_id=source.session_id,
            task_id=source.task_id,
            agent_id=source.agent_id,
            trace_id=source.trace_id,
        )

    def envelope(
        self,
        context: ChannelContext,
        payload: Mapping[str, object],
        *,
        message_id: str | None = None,
        sequence: int = 0,
    ) -> ChannelEnvelope:
        if sequence < 0:
            raise WorkspaceError("sequence cannot be negative")
        return ChannelEnvelope(
            message_id=message_id or f"msg_{secrets.token_hex(12)}",
            channel_id=context.channel_id,
            workspace_id=context.workspace_id,
            session_id=context.session_id,
            task_id=context.task_id,
            agent_id=context.agent_id,
            trace_id=context.trace_id,
            payload=dict(payload),
            sequence=sequence,
        )

    def emit(self, envelope: ChannelEnvelope) -> None:
        context = self._channel(envelope.channel_id)
        if context is None:
            raise WorkspaceError("channel does not exist")
        if str(context["workspace_id"]) != envelope.workspace_id:
            raise WorkspaceError("channel envelope workspace mismatch")
        self.store.append_channel_message(
            (
                envelope.message_id,
                envelope.channel_id,
                envelope.workspace_id,
                envelope.session_id,
                envelope.task_id,
                envelope.agent_id,
                envelope.trace_id,
                envelope.sequence,
                json.dumps(dict(envelope.payload), sort_keys=True),
                utc_now().isoformat(),
            )
        )

    def adapter(self, context: ChannelContext) -> ChannelAdapter:
        adapters = {
            ChannelKind.WEB: WebChannel,
            ChannelKind.CLI: CLIChannel,
            ChannelKind.DESKTOP: DesktopChannel,
            ChannelKind.API: APIChannel,
            ChannelKind.MESSAGING: MessagingChannel,
            ChannelKind.NOTIFICATIONS: NotificationChannel,
        }
        return adapters[context.kind](self, context)

    def workspace_snapshot(self, workspace_id: str) -> WorkspaceSnapshot:
        if not self._workspace_exists(workspace_id):
            raise WorkspaceError("workspace does not exist")
        rows = self.store.query(
            "SELECT resource_type, resource_id FROM workspace_resources "
            "WHERE workspace_id=? ORDER BY resource_type, resource_id",
            (workspace_id,),
        )
        grouped: dict[str, list[str]] = {}
        for row in rows:
            grouped.setdefault(str(row["resource_type"]), []).append(str(row["resource_id"]))
        table_map = {
            "agents": "agents",
            "sessions": "sessions",
            "tasks": "tasks",
            "workflows": "workflows",
            "memory": "memory_records",
            "events": "events",
        }
        for resource_type, table in table_map.items():
            rows = self.store.query(
                f"SELECT * FROM {table} WHERE workspace_id=?",
                (workspace_id,),
            )
            if resource_type == "memory":
                grouped[resource_type] = [str(row["memory_id"]) for row in rows]
            else:
                grouped[resource_type] = [str(row[f"{resource_type[:-1]}_id"]) for row in rows]
        channels = self.store.query(
            "SELECT channel_id FROM channels WHERE workspace_id=? ORDER BY channel_id",
            (workspace_id,),
        )
        grouped["channels"] = [str(row["channel_id"]) for row in channels]
        return WorkspaceSnapshot(
            workspace_id=workspace_id,
            agents=tuple(grouped.get("agents", ())),
            applications=tuple(grouped.get("applications", ())),
            skills=tuple(grouped.get("skills", ())),
            sessions=tuple(grouped.get("sessions", ())),
            tasks=tuple(grouped.get("tasks", ())),
            workflows=tuple(grouped.get("workflows", ())),
            memory=tuple(grouped.get("memory", ())),
            integrations=tuple(grouped.get("integrations", ())),
            events=tuple(grouped.get("events", ())),
            channels=tuple(grouped.get("channels", ())),
        )

    def register_resource(
        self,
        *,
        workspace_id: str,
        resource_type: str,
        resource_id: str,
        state: str = "active",
        metadata: Mapping[str, object] | None = None,
    ) -> None:
        if not resource_type.strip() or not resource_id.strip():
            raise WorkspaceError("resource type and id are required")
        if not self._workspace_exists(workspace_id):
            raise WorkspaceError("workspace does not exist")
        self.store.upsert_workspace_resource(
            (
                workspace_id,
                resource_type,
                resource_id,
                state,
                json.dumps(dict(metadata or {}), sort_keys=True),
                utc_now().isoformat(),
            )
        )

    def _workspace_exists(self, workspace_id: str) -> bool:
        return bool(
            self.store.query(
                "SELECT workspace_id FROM workspaces WHERE workspace_id=?",
                (workspace_id,),
            )
        )

    def _channel(self, channel_id: str) -> sqlite3.Row | None:
        rows = self.store.query("SELECT * FROM channels WHERE channel_id=?", (channel_id,))
        return rows[0] if rows else None

    def _session(self, session_id: str) -> sqlite3.Row | None:
        rows = self.store.query("SELECT * FROM sessions WHERE session_id=?", (session_id,))
        return rows[0] if rows else None

    def _task(self, task_id: str) -> sqlite3.Row | None:
        rows = self.store.query("SELECT * FROM tasks WHERE task_id=?", (task_id,))
        return rows[0] if rows else None

    @staticmethod
    def _require_workspace(actual: str, expected: str) -> None:
        if actual != expected:
            raise WorkspaceError("cross-workspace lifecycle binding denied")
