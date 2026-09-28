from tinlance_agent_os.domain import AgentId, SessionId, Task, TaskId, TaskStatus, WorkspaceId
from tinlance_agent_os.platform import PlatformRun
from tinlance_agent_os.service import TaskService


class FakePlatform:
    def __init__(self) -> None:
        self.started: list[str] = []
        self.cancelled: list[str] = []

    def list_agents(self):
        return ()

    def start_run(self, task):
        run = PlatformRun("run-1", "corr-1", "running")
        self.started.append(str(task.task_id))
        return run

    def cancel_run(self, run_id):
        self.cancelled.append(str(run_id))

    def get_run(self, run_id):
        return PlatformRun(run_id, "corr-1", "running")

    def get_events(self, correlation_id):
        return ()

    def get_evidence(self, run_id):
        return ()


def test_task_service_delegates_execution_to_platform() -> None:
    platform = FakePlatform()
    task = Task(TaskId("task-1"), WorkspaceId("ws-1"), SessionId("session-1"),
                AgentId("agent-1"), "test")
    result = TaskService(platform).start(task)
    assert result.status is TaskStatus.RUNNING
    assert result.platform_run_ids == ("run-1",)
    assert platform.started == ["task-1"]


def test_task_service_delegates_cancellation_to_platform() -> None:
    platform = FakePlatform()
    task = Task(TaskId("task-1"), WorkspaceId("ws-1"), SessionId("session-1"),
                AgentId("agent-1"), "test", TaskStatus.RUNNING, ("run-1",))
    result = TaskService(platform).cancel(task)
    assert result.status is TaskStatus.CANCELLED
    assert platform.cancelled == ["run-1"]
