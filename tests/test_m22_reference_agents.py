from __future__ import annotations

from types import SimpleNamespace

import pytest

from tinlance_agent_os.reference_agents import (
    CybersecurityAgent,
    FDEEngineeringAgent,
    ResearchAgent,
    WorldIntelligenceAgent,
)


class FakeSDK:
    def __init__(self) -> None:
        self.calls: list[str] = []

    def task(self, session, intent):
        self.calls.append("task")
        return SimpleNamespace(
            task=SimpleNamespace(
                workspace_id="ws-1",
                task_id="task-1",
                session_id="session-1",
                agent_id="agent-1",
            ),
            context=SimpleNamespace(
                trace=SimpleNamespace(traceparent="00-" + "a" * 32 + "-" + "b" * 16 + "-01")
            ),
        )

    def assemble_context(self, retrieval):
        self.calls.append("context")
        return SimpleNamespace()

    def model(self, request):
        self.calls.append("model")
        return SimpleNamespace(usage=SimpleNamespace(input_tokens=1, output_tokens=1))

    def remember(self, write):
        self.calls.append("memory")
        return SimpleNamespace()

    def execute(self, task):
        self.calls.append("execute")
        return SimpleNamespace(run=SimpleNamespace(run_id="run-1"))

    def approve(self, execution, *, action, resource, reason):
        self.calls.append("approval")
        return SimpleNamespace()


class FakeSkills:
    def invoke(self, skill_id, *, input_data, context):
        return {"skill": skill_id}


@pytest.mark.parametrize(
    "agent_type",
    [
        ResearchAgent,
        CybersecurityAgent,
        FDEEngineeringAgent,
        WorldIntelligenceAgent,
    ],
)
def test_reference_agent_uses_governed_stack(agent_type):
    sdk = FakeSDK()
    agent = agent_type(sdk=sdk, application=object(), skills=FakeSkills())
    result = agent.execute(
        session=object(),
        intent="perform governed work",
        model_payload={"prompt": "untrusted model input"},
        skill_id="canonical.skill",
        skill_input={"value": "input"},
        approval=("change", "resource-1", "human approval required"),
    )

    assert result.execution.run.run_id == "run-1"
    assert sdk.calls == ["task", "context", "model", "memory", "execute", "approval"]
    assert result.traceparent is not None


@pytest.mark.parametrize(
    "agent_type",
    [
        ResearchAgent,
        CybersecurityAgent,
        FDEEngineeringAgent,
        WorldIntelligenceAgent,
    ],
)
def test_reference_agents_declare_capabilities(agent_type):
    capabilities = agent_type.capabilities()
    assert capabilities
    assert all(item.capability_id and item.reason for item in capabilities)
