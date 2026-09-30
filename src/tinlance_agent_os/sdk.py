"""High-level Agent Developer SDK (M13).

This module is the supported developer surface above the Agent Platform client.
It composes OS lifecycle/session/task/workflow primitives and Platform references;
it never implements authority locally.
"""

from __future__ import annotations

import hashlib
import json
import re
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass, field, replace
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any, Callable, Iterator, Mapping, cast

from .agent_runtime import AgentDefinition, AgentRuntime, RestartPolicy, RuntimeConfig
from .applications import AgentManifest, CapabilityRequest
from .contracts import AgentPlatformClient
from .domain import ApprovalRef, Event, EvidenceRef, PlatformRunRef, Session, Task
from .errors import PlatformAdapterError
from .store import StateStore
from .workflow import WorkflowDefinition, WorkflowEngine, WorkflowExecution

_HEX32 = re.compile(r"^[0-9a-f]{32}$")
_TRACEPARENT = re.compile(r"^00-[0-9a-f]{32}-[0-9a-f]{16}-[0-9a-f]{2}$")
_current_context: ContextVar["ExecutionContext | None"] = ContextVar(
    "tinlance_agent_os_execution_context", default=None
)


class SDKError(RuntimeError):
    """Base error for developer-surface failures."""


class ContractValidationError(SDKError, ValueError):
    """A public SDK contract failed validation."""


class SDKPlatformError(SDKError):
    """A Platform operation failed through the SDK boundary."""

    def __init__(self, operation: str, cause: Exception) -> None:
        super().__init__(f"{operation} failed: {cause}")
        self.operation = operation
        self.cause = cause
        self.retryable = isinstance(cause, (TimeoutError, ConnectionError))


class IdempotencyError(SDKError, ValueError):
    """An idempotency key is invalid."""


class AgentCapabilityError(SDKError, ValueError):
    """A capability declaration is invalid."""


class ApprovalState(StrEnum):
    REQUESTED = "requested"


@dataclass(frozen=True, slots=True)
class TraceContext:
    """Immutable W3C trace context propagated across SDK calls."""

    traceparent: str

    def __post_init__(self) -> None:
        if not _TRACEPARENT.fullmatch(self.traceparent):
            raise ContractValidationError("traceparent must be a valid W3C traceparent")


@dataclass(frozen=True, slots=True)
class ExecutionContext:
    """Correlation context carried through agent, task and Platform operations."""

    trace: TraceContext | None = None
    baggage: Mapping[str, str] = field(default_factory=dict)
    session_id: str | None = None
    task_id: str | None = None
    workflow_id: str | None = None

    def child(
        self,
        *,
        session_id: str | None = None,
        task_id: str | None = None,
        workflow_id: str | None = None,
    ) -> "ExecutionContext":
        return replace(
            self,
            session_id=session_id if session_id is not None else self.session_id,
            task_id=task_id if task_id is not None else self.task_id,
            workflow_id=workflow_id if workflow_id is not None else self.workflow_id,
        )


@dataclass(frozen=True, slots=True)
class CapabilityDeclaration:
    """Developer declaration only; Platform decides actual authority."""

    capability_id: str
    reason: str
    optional: bool = False

    def validate(self) -> None:
        if not self.capability_id.strip() or not self.reason.strip():
            raise AgentCapabilityError("capability_id and reason are required")
        if any(character in self.capability_id for character in "\x00\r\n"):
            raise AgentCapabilityError("capability_id contains invalid characters")


@dataclass(frozen=True, slots=True)
class IdempotencyKey:
    value: str

    def __post_init__(self) -> None:
        if not self.value or self.value != self.value.strip() or len(self.value) > 255:
            raise IdempotencyError("idempotency key must be 1-255 normalized characters")

    @classmethod
    def deterministic(cls, *, agent_id: str, operation: str, subject: str) -> "IdempotencyKey":
        canonical = json.dumps(
            {"agent_id": agent_id, "operation": operation, "subject": subject},
            sort_keys=True,
            separators=(",", ":"),
        )
        return cls(hashlib.sha256(canonical.encode()).hexdigest())


@dataclass(frozen=True, slots=True)
class ExecutionResult:
    """Typed result from a governed Platform run."""

    run: PlatformRunRef
    events: tuple[Event, ...] = ()
    evidence: tuple[EvidenceRef, ...] = ()

    @property
    def state(self) -> str:
        return self.run.state


@dataclass(frozen=True, slots=True)
class ApprovalWorkflow:
    """Opaque Platform approval request; approval authority remains remote."""

    reference: ApprovalRef
    state: ApprovalState
    action: str
    resource: str
    reason: str
    run_id: str


@dataclass(frozen=True, slots=True)
class AgentScaffold:
    """Complete developer artifact returned by scaffold()."""

    manifest: AgentManifest
    definition: AgentDefinition
    capabilities: tuple[CapabilityDeclaration, ...]


@dataclass(frozen=True, slots=True)
class AgentApplication:
    """A validated agent package definition without a second runtime authority."""

    scaffold: AgentScaffold

    def runtime(
        self,
        store: StateStore,
        handler: Callable[[Mapping[str, object]], object],
    ) -> AgentRuntime:
        return AgentRuntime(store, self.scaffold.definition, handler)


@dataclass(frozen=True, slots=True)
class SessionHandle:
    session: Session
    context: ExecutionContext


@dataclass(frozen=True, slots=True)
class TaskHandle:
    task: Task
    context: ExecutionContext


@dataclass(frozen=True, slots=True)
class WorkflowHandle:
    definition: WorkflowDefinition
    execution: WorkflowExecution
    context: ExecutionContext


@dataclass(slots=True)
class AgentSDK:
    """The official high-level developer surface for Tinlance Agent OS."""

    platform: AgentPlatformClient
    store: StateStore
    workflow_engine: WorkflowEngine = field(default_factory=WorkflowEngine)

    @staticmethod
    def validate_manifest(manifest: AgentManifest) -> AgentManifest:
        manifest.validate()
        if manifest.entrypoint != manifest.entrypoint.strip():
            raise ContractValidationError("manifest entrypoint must be normalized")
        return manifest

    @staticmethod
    def validate_capabilities(
        declarations: tuple[CapabilityDeclaration, ...],
    ) -> tuple[CapabilityDeclaration, ...]:
        ids = set()
        for declaration in declarations:
            declaration.validate()
            if declaration.capability_id in ids:
                raise AgentCapabilityError("duplicate capability declaration")
            ids.add(declaration.capability_id)
        return declarations

    def scaffold(
        self,
        *,
        agent_id: str,
        workspace_id: str,
        name: str,
        version: str,
        entrypoint: str,
        capabilities: tuple[CapabilityDeclaration, ...] = (),
        configuration: Mapping[str, object] | None = None,
        restart_policy: RestartPolicy | None = None,
        runtime: RuntimeConfig | None = None,
        min_os_version: str = "0.1.0",
    ) -> AgentApplication:
        declarations = self.validate_capabilities(capabilities)
        requests = tuple(
            CapabilityRequest(item.capability_id, item.reason, item.optional)
            for item in declarations
        )
        manifest = self.validate_manifest(
            AgentManifest(
                application_id=agent_id,
                name=name,
                version=version,
                min_os_version=min_os_version,
                entrypoint=entrypoint,
                capabilities=requests,
            )
        )
        definition = AgentDefinition(
            agent_id=agent_id,
            workspace_id=workspace_id,
            name=name,
            version=version,
            entrypoint=entrypoint,
            capabilities=tuple(item.capability_id for item in declarations),
            configuration=dict(configuration or {}),
            restart_policy=restart_policy or RestartPolicy(),
            runtime=runtime or RuntimeConfig(),
        )
        try:
            definition.validate()
        except ValueError as exc:
            raise ContractValidationError(str(exc)) from exc
        return AgentApplication(AgentScaffold(manifest, definition, declarations))

    def register(self, application: AgentApplication) -> AgentRuntime:
        runtime = application.runtime(self.store, lambda _: None)
        try:
            runtime.register()
        except Exception as exc:
            raise self._wrap("agent.register", exc)
        return runtime

    def session(self, workspace_id: str, user_id: str, agent_id: str) -> SessionHandle:
        try:
            from .daemon_service import LocalOSService

            service = LocalOSService(self.store, self.platform)
            session = service.create_session(workspace_id, user_id, agent_id)
        except Exception as exc:
            raise self._wrap("session.create", exc)
        return SessionHandle(session, self._context().child(session_id=session.session_id))

    def task(
        self,
        session: SessionHandle,
        intent: str,
        *,
        dependencies: tuple[str, ...] = (),
    ) -> TaskHandle:
        try:
            from .daemon_service import LocalOSService

            service = LocalOSService(self.store, self.platform)
            task = service.create_task(
                session.session.workspace_id,
                session.session.session_id,
                session.session.agent_id,
                intent,
                dependencies,
            )
        except Exception as exc:
            raise self._wrap("task.create", exc)
        return TaskHandle(task, session.context.child(task_id=task.task_id))

    def execute(
        self,
        task: TaskHandle,
        *,
        idempotency_key: IdempotencyKey | None = None,
    ) -> ExecutionResult:
        key = idempotency_key or IdempotencyKey.deterministic(
            agent_id=task.task.agent_id,
            operation="task.execute",
            subject=task.task.task_id,
        )
        if not key.value:
            raise IdempotencyError("idempotency key is required")
        try:
            stored = self.store.get_task(task.task.task_id)
            if stored is None:
                raise ContractValidationError("task is not durably registered")
            existing_ids = tuple(json.loads(stored["platform_run_ids"]))
            platform = self._platform_for_context(task.context)
            if existing_ids:
                run_id = existing_ids[0]
                events = tuple(platform.get_events(run_id=run_id))
                evidence = tuple(platform.get_evidence(run_id=run_id))
                return ExecutionResult(
                    PlatformRunRef(run_id, task.task.task_id, stored["state"]),
                    events,
                    evidence,
                )
            completed, result_id = self.store.claim_idempotency(
                idempotency_key=key.value,
                operation="task.execute",
                subject_id=task.task.task_id,
                now=datetime.now(UTC).isoformat(),
            )
            if completed:
                if not result_id:
                    raise IdempotencyError("completed idempotency record has no result")
                run = PlatformRunRef(result_id, task.task.task_id, stored["state"])
            else:
                run = platform.create_run(
                    task_id=task.task.task_id,
                    agent_id=task.task.agent_id,
                    intent=task.task.intent,
                    idempotency_key=key.value,
                )
                self.store.complete_idempotency(
                    idempotency_key=key.value,
                    result_id=run.run_id,
                    now=datetime.now(UTC).isoformat(),
                )
            events = tuple(platform.get_events(run_id=run.run_id))
            evidence = tuple(platform.get_evidence(run_id=run.run_id))
            return ExecutionResult(run, events, evidence)
        except SDKError:
            raise
        except Exception as exc:
            raise self._wrap(f"task.execute:{key.value}", exc)

    def approve(
        self,
        execution: ExecutionResult,
        *,
        action: str,
        resource: str,
        reason: str,
        idempotency_key: IdempotencyKey | None = None,
    ) -> ApprovalWorkflow:
        if not all(value.strip() for value in (action, resource, reason)):
            raise ContractValidationError("approval action, resource and reason are required")
        key = idempotency_key or IdempotencyKey.deterministic(
            agent_id=self._agent_for_run(execution.run.run_id),
            operation="approval.request",
            subject=f"{execution.run.run_id}:{action}:{resource}",
        )
        try:
            platform = self._platform_for_context(self._context())
            completed, result_id = self.store.claim_idempotency(
                idempotency_key=key.value,
                operation="approval.request",
                subject_id=execution.run.run_id,
                now=datetime.now(UTC).isoformat(),
            )
            if completed:
                if not result_id:
                    raise IdempotencyError("completed approval record has no result")
                approval = ApprovalRef(result_id)
            else:
                approval = platform.request_approval(
                    run_id=execution.run.run_id,
                    action=action,
                    resource=resource,
                    reason=reason,
                    idempotency_key=key.value,
                )
                self.store.complete_idempotency(
                    idempotency_key=key.value,
                    result_id=approval.approval_id,
                    now=datetime.now(UTC).isoformat(),
                )
            return ApprovalWorkflow(
                approval,
                ApprovalState.REQUESTED,
                action,
                resource,
                reason,
                execution.run.run_id,
            )
        except Exception as exc:
            raise self._wrap(f"approval.request:{key.value}", exc)

    def result(
        self,
        run: PlatformRunRef,
    ) -> ExecutionResult:
        try:
            platform = self._platform_for_context(self._context())
            return ExecutionResult(
                run,
                tuple(platform.get_events(run_id=run.run_id)),
                tuple(platform.get_evidence(run_id=run.run_id)),
            )
        except Exception as exc:
            raise self._wrap("execution.result", exc)

    def workflow(
        self,
        definition: WorkflowDefinition,
        *,
        context: ExecutionContext | None = None,
    ) -> WorkflowHandle:
        try:
            execution = self.workflow_engine.start(definition)
        except Exception as exc:
            raise self._wrap("workflow.start", exc)
        return WorkflowHandle(
            definition,
            execution,
            (context or self._context()).child(workflow_id=definition.workflow_id),
        )

    def workflow_complete_step(
        self,
        workflow: WorkflowHandle,
        step_id: str,
    ) -> WorkflowHandle:
        try:
            execution = self.workflow_engine.complete_step(
                workflow.definition,
                workflow.execution,
                step_id,
            )
        except Exception as exc:
            raise self._wrap("workflow.complete_step", exc)
        return replace(workflow, execution=execution)

    def workflow_fail_step(self, workflow: WorkflowHandle, step_id: str) -> WorkflowHandle:
        try:
            execution = self.workflow_engine.fail_step(
                workflow.definition,
                workflow.execution,
                step_id,
            )
        except Exception as exc:
            raise self._wrap("workflow.fail_step", exc)
        return replace(workflow, execution=execution)

    def workflow_cancel(self, workflow: WorkflowHandle) -> WorkflowHandle:
        try:
            execution = self.workflow_engine.cancel(
                workflow.definition,
                workflow.execution,
            )
        except Exception as exc:
            raise self._wrap("workflow.cancel", exc)
        return replace(workflow, execution=execution)

    @contextmanager
    def context(self, context: ExecutionContext) -> Iterator[ExecutionContext]:
        token = _current_context.set(context)
        try:
            yield context
        finally:
            _current_context.reset(token)

    def current_context(self) -> ExecutionContext:
        return self._context()

    def _context(self) -> ExecutionContext:
        return _current_context.get() or ExecutionContext()

    def _platform_for_context(self, context: ExecutionContext) -> AgentPlatformClient:
        platform = self.platform
        trace = context.trace
        if trace is not None:
            with_trace = getattr(platform, "with_trace_context", None)
            if callable(with_trace):
                return cast(AgentPlatformClient, with_trace(trace.traceparent))
        return platform

    def _agent_for_run(self, run_id: str) -> str:
        row = self.store.find_task_by_platform_run(run_id)
        if row is None:
            raise ContractValidationError("run is not bound to a durable OS task")
        return cast(str, row["agent_id"])

    @staticmethod
    def _wrap(operation: str, exc: Exception) -> SDKError:
        if isinstance(exc, PlatformAdapterError):
            return SDKPlatformError(operation, exc)
        if isinstance(exc, (ContractValidationError, IdempotencyError, AgentCapabilityError)):
            return exc
        return SDKError(f"{operation} failed: {exc}")
