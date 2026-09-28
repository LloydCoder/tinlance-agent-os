from datetime import UTC, datetime

from tinlance_agent_os.domain import AgentId, CorrelationId, Event, EventId, RunId
from tinlance_agent_os.domain import Session, SessionId, Task, TaskId, TaskStatus
from tinlance_agent_os.domain import UserId, WorkspaceId


def test_task_is_os_lifecycle_state_not_authority() -> None:
    task = Task(TaskId("task-1"), WorkspaceId("ws-1"), SessionId("session-1"),
                AgentId("agent-1"), "deploy")
    assert task.status is TaskStatus.CREATED
    assert task.platform_run_ids == ()


def test_session_belongs_to_workspace_and_user() -> None:
    session = Session(SessionId("session-1"), WorkspaceId("ws-1"), UserId("user-1"),
                      AgentId("agent-1"))
    assert session.workspace_id == WorkspaceId("ws-1")
    assert session.user_id == UserId("user-1")


def test_event_has_correlation_and_optional_platform_run() -> None:
    event = Event(EventId("event-1"), "task.created", datetime.now(UTC),
                  WorkspaceId("ws-1"), CorrelationId("corr-1"), RunId("run-1"),
                  "agent-os", {})
    assert event.platform_run_id == RunId("run-1")
