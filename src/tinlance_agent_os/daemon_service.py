"""OS daemon application service: local lifecycle only, Platform for authority."""
from __future__ import annotations
from dataclasses import dataclass
from uuid import uuid4
from .contracts import AgentPlatformClient
from .daemon import AgentOSDaemon, DaemonConfig
from .domain import Task, TaskState, Workspace, Session, SessionState, utc_now
from .store import StateStore

@dataclass(slots=True)
class LocalOSService:
    store: StateStore
    platform: AgentPlatformClient
    def create_workspace(self, owner_user_id: str) -> Workspace:
        ws=Workspace(str(uuid4()),owner_user_id); self.store.upsert_workspace(ws.workspace_id,ws.owner_user_id,utc_now().isoformat()); return ws
    def create_session(self, workspace_id: str, user_id: str, agent_id: str) -> Session:
        s=Session(str(uuid4()),workspace_id,user_id,agent_id); self.store.upsert_session((s.session_id,s.workspace_id,s.user_id,s.agent_id,s.state.value,utc_now().isoformat())); return s
    def create_task(self, workspace_id: str, session_id: str, agent_id: str, intent: str, dependencies: tuple[str,...]=()) -> Task:
        if not intent.strip(): raise ValueError("intent is required")
        t=Task(str(uuid4()),workspace_id,session_id,agent_id,intent,TaskState.CREATED,dependencies)
        self.store.upsert_task((t.task_id,t.workspace_id,t.session_id,t.agent_id,t.intent,t.state.value,json.dumps(dependencies),json.dumps(()),t.created_at.isoformat())); return t
    def dispatch(self, task: Task):
        run=self.platform.create_run(task_id=task.task_id,agent_id=task.agent_id,intent=task.intent)
        self.store.upsert_task((task.task_id,task.workspace_id,task.session_id,task.agent_id,task.intent,TaskState.RUNNING.value,json.dumps(tuple(task.dependencies)),json.dumps((run.run_id,)),task.created_at.isoformat()))
        return run
    def daemon(self, socket_path: str) -> AgentOSDaemon:
        return AgentOSDaemon(DaemonConfig(Path(socket_path)), self.handle)
    def handle(self, request: dict[str, object]) -> dict[str, object]:
        op=request.get("operation")
        if op=="health": return {"ready": self.platform.health()}
        if op=="principal": return {"user_id": self.platform.get_principal().user_id}
        raise ValueError("unsupported operation")
