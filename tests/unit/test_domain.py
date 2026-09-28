from datetime import timezone

from tinlance_agent_os.domain import SessionState, Task, TaskState, utc_now


def test_task_defaults_are_os_state_only() -> None:
    now = utc_now()
    task = Task(
        task_id="task-1",
        workspace_id="ws-1",
        session_id="session-1",
        agent_id="agent-1",
        intent="inspect repository",
        created_at=now,
    )
    assert task.state is TaskState.CREATED
    assert task.platform_run_ids == ()
    assert now.tzinfo is timezone.utc
    assert SessionState.ACTIVE.value == "active"
