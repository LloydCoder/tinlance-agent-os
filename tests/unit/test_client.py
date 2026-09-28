from tinlance_agent_os.client import ReferenceAgentPlatformClient
from tinlance_agent_os.domain import Agent, TaskState


def test_reference_client_delegates_execution_boundary() -> None:
    client = ReferenceAgentPlatformClient(agents=[Agent("agent-1", "Builder", "1.0.0")])
    run = client.create_run(
        task_id="task-1",
        agent_id="agent-1",
        intent="build",
    )
    assert run.state == TaskState.RUNNING.value

    cancelled = client.cancel_run(run_id=run.run_id)
    assert cancelled.state == TaskState.CANCELLED.value


def test_reference_client_returns_platform_references() -> None:
    client = ReferenceAgentPlatformClient()
    assert client.health() is True
    assert client.get_evidence(run_id="run-1")[0].source == "agent-platform"
    assert client.request_approval(run_id="run-1", action="deploy").source == "agent-platform"
