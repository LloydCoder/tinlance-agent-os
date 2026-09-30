"""Canonical Tinlance reference agents built only on Agent OS surfaces."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from .applications import CapabilityRequest
from .model_gateway import ModelRequest, ModelResponse, ModelTask
from .sdk import AgentApplication, AgentSDK, ExecutionResult, SessionHandle, TaskHandle
from .memory import AssembledContext, MemoryRetrieval


class SkillInvoker(Protocol):
    """Non-authoritative skill execution surface.

    A skill may transform or inspect data, but it cannot create Platform
    authority. Consequential actions must still flow through AgentSDK.execute.
    """

    def invoke(self, skill_id: str, *, input_data: object, context: TaskHandle) -> object: ...


@dataclass(frozen=True, slots=True)
class ReferenceAgentResult:
    agent_id: str
    task: TaskHandle
    model_response: ModelResponse | None
    skill_output: object | None
    context: AssembledContext | None
    execution: ExecutionResult
    traceparent: str | None


@dataclass(frozen=True, slots=True)
class ReferenceAgent:
    """Common governed execution path shared by every reference agent."""

    sdk: AgentSDK
    application: AgentApplication
    skills: SkillInvoker

    def execute(
        self,
        *,
        session: SessionHandle,
        intent: str,
        model_payload: object | None = None,
        model_task: ModelTask = ModelTask.CHAT,
        skill_id: str | None = None,
        skill_input: object | None = None,
        approval: tuple[str, str, str] | None = None,
    ) -> ReferenceAgentResult:
        task = self.sdk.task(session, intent)
        context = self.sdk.assemble_context(
            MemoryRetrieval(
                query=intent,
                workspace_id=task.task.workspace_id,
                agent_id=task.task.agent_id,
                session_id=task.task.session_id,
                task_id=task.task.task_id,
            )
        )
        skill_output = None
        if skill_id is not None:
            skill_output = self.skills.invoke(
                skill_id,
                input_data=skill_input if skill_input is not None else intent,
                context=task,
            )

        model_response = None
        if model_payload is not None:
            model_response = self.sdk.model(
                ModelRequest(
                    task=model_task,
                    payload=model_payload,
                    metadata={"reference_agent": task.task.agent_id},
                )
            )

        self.sdk.remember(
            self._memory_write(
                task,
                intent=intent,
                model_response=model_response,
                skill_output=skill_output,
            )
        )
        execution = self.sdk.execute(task)
        if approval is not None:
            action, resource, reason = approval
            self.sdk.approve(
                execution,
                action=action,
                resource=resource,
                reason=reason,
            )
        return ReferenceAgentResult(
            agent_id=task.task.agent_id,
            task=task,
            model_response=model_response,
            skill_output=skill_output,
            context=context,
            execution=execution,
            traceparent=task.context.trace.traceparent if task.context.trace else None,
        )

    @staticmethod
    def _memory_write(
        task: TaskHandle,
        *,
        intent: str,
        model_response: ModelResponse | None,
        skill_output: object | None,
    ) -> MemoryWrite:
        from .memory import MemoryProvenance, MemoryScope, MemorySourceType, MemoryWrite

        return MemoryWrite(
            workspace_id=task.task.workspace_id,
            scope=MemoryScope.TASK,
            scope_id=task.task.task_id,
            agent_id=task.task.agent_id,
            content=intent,
            provenance=MemoryProvenance(MemorySourceType.AGENT, task.task.agent_id),
        )


@dataclass(frozen=True, slots=True)
class ResearchAgent(ReferenceAgent):
    """Canonical research and synthesis agent."""

    @staticmethod
    def capabilities() -> tuple[CapabilityRequest, ...]:
        return (
            CapabilityRequest("research.read", "Read approved research sources"),
            CapabilityRequest("research.write", "Persist research findings"),
        )


@dataclass(frozen=True, slots=True)
class CybersecurityAgent(ReferenceAgent):
    """Canonical defensive cybersecurity analysis agent."""

    @staticmethod
    def capabilities() -> tuple[CapabilityRequest, ...]:
        return (
            CapabilityRequest("security.read", "Inspect approved security evidence"),
            CapabilityRequest("security.analyze", "Perform defensive security analysis"),
        )


@dataclass(frozen=True, slots=True)
class FDEEngineeringAgent(ReferenceAgent):
    """Canonical software/FDE engineering agent."""

    @staticmethod
    def capabilities() -> tuple[CapabilityRequest, ...]:
        return (
            CapabilityRequest("engineering.read", "Inspect approved engineering inputs"),
            CapabilityRequest("engineering.write", "Prepare approved engineering changes"),
        )


@dataclass(frozen=True, slots=True)
class WorldIntelligenceAgent(ReferenceAgent):
    """Canonical world-intelligence synthesis agent."""

    @staticmethod
    def capabilities() -> tuple[CapabilityRequest, ...]:
        return (
            CapabilityRequest("world_intelligence.read", "Read approved intelligence sources"),
            CapabilityRequest(
                "world_intelligence.synthesize",
                "Synthesize approved intelligence observations",
            ),
        )
