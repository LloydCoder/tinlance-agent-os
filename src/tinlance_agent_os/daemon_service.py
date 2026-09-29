"""Application service for local Agent OS lifecycle."""

import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from uuid import uuid4

from .contracts import AgentPlatformClient
from .daemon import AgentOSDaemon, DaemonConfig
from .domain import (
    ApprovalRef,
    Event,
    EvidenceRef,
    PlatformRunRef,
    Session,
    Task,
    TaskState,
    Workspace,
    utc_now,
)
from .store import StateStore


def _required_text(request: dict[str, object], key: str) -> str:
    value = request.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{key} is required")
    return value


@dataclass(slots=True)
class LocalOSService:
    store: StateStore
    platform: AgentPlatformClient

    def create_workspace(self, owner_user_id: str) -> Workspace:
        owner_user_id = owner_user_id.strip()
        if not owner_user_id:
            raise ValueError("owner_user_id is required")
        workspace = Workspace(str(uuid4()), owner_user_id)
        self.store.upsert_workspace(
            workspace.workspace_id,
            workspace.owner_user_id,
            utc_now().isoformat(),
        )
        return workspace

    def create_session(self, workspace_id: str, user_id: str, agent_id: str) -> Session:
        if not all(value.strip() for value in (workspace_id, user_id, agent_id)):
            raise ValueError("workspace_id, user_id and agent_id are required")
        rows = self.store.query(
            "SELECT owner_user_id FROM workspaces WHERE workspace_id=?",
            (workspace_id,),
        )
        if not rows or rows[0][0] != user_id:
            raise PermissionError("user is not the workspace owner")
        session = Session(str(uuid4()), workspace_id, user_id, agent_id)
        self.store.upsert_session(
            (
                session.session_id,
                session.workspace_id,
                session.user_id,
                session.agent_id,
                session.state.value,
                utc_now().isoformat(),
            )
        )
        return session

    def create_task(
        self,
        workspace_id: str,
        session_id: str,
        agent_id: str,
        intent: str,
        dependencies: tuple[str, ...] = (),
    ) -> Task:
        if not all(value.strip() for value in (workspace_id, session_id, agent_id, intent)):
            raise ValueError("task fields are required")
        if len(dependencies) != len(set(dependencies)) or any(
            not dependency.strip() for dependency in dependencies
        ):
            raise ValueError("task dependencies must be unique and non-empty")
        rows = self.store.query(
            "SELECT workspace_id,user_id,agent_id,state FROM sessions WHERE session_id=?",
            (session_id,),
        )
        if not rows or rows[0][0] != workspace_id or rows[0][2] != agent_id:
            raise PermissionError("task does not belong to the supplied session/workspace/agent")
        if rows[0][3] != "active":
            raise ValueError("tasks may only be created in active sessions")
        task = Task(
            str(uuid4()),
            workspace_id,
            session_id,
            agent_id,
            intent,
            TaskState.CREATED,
            dependencies,
        )
        self.store.upsert_task(
            (
                task.task_id,
                task.workspace_id,
                task.session_id,
                task.agent_id,
                task.intent,
                task.state.value,
                json.dumps(dependencies),
                json.dumps(()),
                task.created_at.isoformat(),
            )
        )
        return task

    @staticmethod
    def _task_from_row(row: sqlite3.Row) -> Task:
        dependencies = json.loads(row["dependencies"])
        platform_run_ids = json.loads(row["platform_run_ids"])
        if not isinstance(dependencies, list) or not isinstance(platform_run_ids, list):
            raise ValueError("stored task collections are invalid")
        return Task(
            row["task_id"],
            row["workspace_id"],
            row["session_id"],
            row["agent_id"],
            row["intent"],
            TaskState(row["state"]),
            tuple(dependencies),
            tuple(platform_run_ids),
            datetime.fromisoformat(row["created_at"]),
        )

    def dispatch(self, task: Task) -> PlatformRunRef:
        if not task.task_id or not task.agent_id or not task.intent.strip():
            raise ValueError("task is invalid")
        stored = self.store.get_task(task.task_id)
        if stored is None:
            raise PermissionError("task must be created in Agent OS before dispatch")
        stored_task = self._task_from_row(stored)
        if (
            stored_task.workspace_id != task.workspace_id
            or stored_task.session_id != task.session_id
            or stored_task.agent_id != task.agent_id
            or stored_task.intent != task.intent
        ):
            raise PermissionError("task identity does not match durable OS state")
        if stored_task.state not in {TaskState.CREATED, TaskState.READY}:
            raise ValueError("task is not dispatchable")
        run = self.platform.create_run(
            task_id=stored_task.task_id,
            agent_id=stored_task.agent_id,
            intent=stored_task.intent,
        )
        self.store.upsert_task(
            (
                stored_task.task_id,
                stored_task.workspace_id,
                stored_task.session_id,
                stored_task.agent_id,
                stored_task.intent,
                TaskState.RUNNING.value,
                json.dumps(tuple(stored_task.dependencies)),
                json.dumps((*stored_task.platform_run_ids, run.run_id)),
                stored_task.created_at.isoformat(),
            )
        )
        return run

    def cancel(self, run_id: str) -> PlatformRunRef:
        run = self.platform.cancel_run(run_id=run_id)
        task_row = self.store.find_task_by_platform_run(run_id)
        if task_row is not None:
            task = self._task_from_row(task_row)
            self.store.upsert_task(
                (
                    task.task_id,
                    task.workspace_id,
                    task.session_id,
                    task.agent_id,
                    task.intent,
                    TaskState.CANCELLED.value,
                    json.dumps(tuple(task.dependencies)),
                    json.dumps(tuple(task.platform_run_ids)),
                    task.created_at.isoformat(),
                )
            )
        return run

    def request_approval(
        self,
        run_id: str,
        action: str,
        resource: str,
        reason: str,
    ) -> ApprovalRef:
        return self.platform.request_approval(
            run_id=run_id,
            action=action,
            resource=resource,
            reason=reason,
        )

    def events(self, run_id: str) -> tuple[Event, ...]:
        return tuple(self.platform.get_events(run_id=run_id))

    def evidence(self, run_id: str) -> tuple[EvidenceRef, ...]:
        return tuple(self.platform.get_evidence(run_id=run_id))

    def daemon(self, socket_path: str) -> AgentOSDaemon:
        return AgentOSDaemon(DaemonConfig(Path(socket_path).resolve()), self.handle)

    def handle(self, request: dict[str, object]) -> dict[str, object]:
        operation = request.get("operation")
        if not isinstance(operation, str):
            raise ValueError("operation is required")
        if operation == "health":
            return {"ready": self.platform.health()}
        if operation == "principal":
            return {"user_id": self.platform.get_principal().user_id}
        if operation == "agents":
            return {
                "agents": [
                    {"agent_id": agent.agent_id, "name": agent.name, "version": agent.version}
                    for agent in self.platform.list_agents()
                ]
            }
        if operation == "capabilities":
            agent_id = request.get("agent_id")
            if not isinstance(agent_id, str):
                raise ValueError("agent_id is required")
            return {
                "capabilities": [
                    {"capability_id": capability.capability_id}
                    for capability in self.platform.list_capabilities(agent_id=agent_id)
                ]
            }
        if operation == "dispatch":
            task_id = _required_text(request, "task_id")
            stored = self.store.get_task(task_id)
            if stored is None:
                raise PermissionError("task must be created before dispatch")
            task = self._task_from_row(stored)
            run = self.dispatch(task)
            return {"run_id": run.run_id, "task_id": run.task_id, "state": run.state}
        if operation == "cancel":
            run_id = request.get("run_id")
            if not isinstance(run_id, str):
                raise ValueError("run_id is required")
            run = self.cancel(run_id)
            return {"run_id": run.run_id, "task_id": run.task_id, "state": run.state}
        if operation == "approval":
            run_id = _required_text(request, "run_id")
            action = _required_text(request, "action")
            resource = _required_text(request, "resource")
            reason = _required_text(request, "reason")
            approval = self.request_approval(run_id, action, resource, reason)
            task_row = self.store.find_task_by_platform_run(run_id)
            if task_row is not None:
                task = self._task_from_row(task_row)
                self.store.upsert_task(
                    (
                        task.task_id,
                        task.workspace_id,
                        task.session_id,
                        task.agent_id,
                        task.intent,
                        TaskState.WAITING_APPROVAL.value,
                        json.dumps(tuple(task.dependencies)),
                        json.dumps(tuple(task.platform_run_ids)),
                        task.created_at.isoformat(),
                    )
                )
            return {"approval_id": approval.approval_id}
        if operation == "events":
            run_id = request.get("run_id")
            if not isinstance(run_id, str):
                raise ValueError("run_id is required")
            return {
                "events": [
                    {
                        "event_id": event.event_id,
                        "event_type": event.event_type,
                        "occurred_at": event.occurred_at.isoformat(),
                        "workspace_id": event.workspace_id,
                        "session_id": event.session_id,
                        "task_id": event.task_id,
                        "agent_id": event.agent_id,
                        "platform_run_id": event.platform_run_id,
                        "correlation_id": event.correlation_id,
                        "source": event.source,
                        "payload": dict(event.payload),
                    }
                    for event in self.events(run_id)
                ]
            }
        if operation == "evidence":
            run_id = request.get("run_id")
            if not isinstance(run_id, str):
                raise ValueError("run_id is required")
            return {
                "evidence": [
                    {"evidence_id": item.evidence_id, "source": item.source}
                    for item in self.evidence(run_id)
                ]
            }
        raise ValueError("unsupported operation")
