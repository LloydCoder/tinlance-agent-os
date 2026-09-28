"""Application service for local Agent OS lifecycle."""

import json
from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4

from .contracts import AgentPlatformClient
from .daemon import AgentOSDaemon, DaemonConfig
from .domain import Session, Task, TaskState, Workspace, utc_now
from .store import StateStore


@dataclass(slots=True)
class LocalOSService:
    store: StateStore
    platform: AgentPlatformClient

    def create_workspace(self, owner_user_id: str) -> Workspace:
        if not owner_user_id.strip():
            raise ValueError("owner_user_id is required")
        workspace = Workspace(str(uuid4()), owner_user_id)
        self.store.upsert_workspace(
            workspace.workspace_id,
            workspace.owner_user_id,
            utc_now().isoformat(),
        )
        return workspace

    def create_session(self, workspace_id: str, user_id: str, agent_id: str) -> Session:
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
        if not intent.strip():
            raise ValueError("intent is required")
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

    def dispatch(self, task: Task):
        run = self.platform.create_run(
            task_id=task.task_id,
            agent_id=task.agent_id,
            intent=task.intent,
        )
        self.store.upsert_task(
            (
                task.task_id,
                task.workspace_id,
                task.session_id,
                task.agent_id,
                task.intent,
                TaskState.RUNNING.value,
                json.dumps(tuple(task.dependencies)),
                json.dumps((run.run_id,)),
                task.created_at.isoformat(),
            )
        )
        return run

    def daemon(self, socket_path: str) -> AgentOSDaemon:
        return AgentOSDaemon(DaemonConfig(Path(socket_path)), self.handle)

    def handle(self, request: dict[str, object]) -> dict[str, object]:
        operation = request.get("operation")
        if operation == "health":
            return {"ready": self.platform.health()}
        if operation == "principal":
            return {"user_id": self.platform.get_principal().user_id}
        raise ValueError("unsupported operation")
