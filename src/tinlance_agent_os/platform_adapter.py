"""Concrete Agent Platform adapter for Agent OS."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, replace
from datetime import datetime
from typing import cast
from uuid import uuid4

from .client import AgentPlatformClient
from .domain import Agent, ApprovalRef, CapabilityRef, Event, EvidenceRef, PlatformRunRef, User
from .errors import PlatformProtocolError
from .transport import PlatformRequestContext, PlatformTransport


def _string(payload: Mapping[str, object], key: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value:
        raise PlatformProtocolError(f"Platform payload field {key!r} must be a non-empty string")
    return value


def _mapping(value: object, key: str) -> Mapping[str, object]:
    if not isinstance(value, dict):
        raise PlatformProtocolError(f"Platform payload field {key!r} must be an object")
    return cast(Mapping[str, object], value)


def _sequence(payload: Mapping[str, object], key: str) -> Sequence[Mapping[str, object]]:
    value = payload.get(key)
    if not isinstance(value, list):
        raise PlatformProtocolError(f"Platform payload field {key!r} must be a list")
    result: list[Mapping[str, object]] = []
    for item in value:
        if not isinstance(item, dict):
            raise PlatformProtocolError(f"Platform payload field {key!r} contains a non-object")
        result.append(cast(Mapping[str, object], item))
    return result


@dataclass(frozen=True, slots=True)
class AgentPlatformAdapter(AgentPlatformClient):
    """Maps OS operations to the versioned Platform API contract.

    The adapter contains no authorization, policy, approval validation or execution
    implementation. Those decisions remain entirely in Agent Platform.
    """

    transport: PlatformTransport
    context: PlatformRequestContext

    def _call(
        self,
        operation: str,
        payload: Mapping[str, object],
        *,
        idempotent: bool,
    ) -> Mapping[str, object]:
        request_context = replace(self.context, request_id=str(uuid4()))
        return self.transport.send(
            operation=operation,
            payload=payload,
            context=request_context,
            idempotent=idempotent,
        )

    def get_principal(self) -> User:
        payload = self._call("principal.get", {}, idempotent=True)
        return User(_string(payload, "user_id"))

    def list_agents(self) -> Sequence[Agent]:
        return tuple(
            Agent(
                _string(item, "agent_id"),
                _string(item, "name"),
                _string(item, "version"),
            )
            for item in _sequence(self._call("agents.list", {}, idempotent=True), "agents")
        )

    def create_run(self, *, task_id: str, agent_id: str, intent: str) -> PlatformRunRef:
        payload = self._call(
            "runs.create",
            {"task_id": task_id, "agent_id": agent_id, "intent": intent},
            idempotent=False,
        )
        return PlatformRunRef(
            _string(payload, "run_id"),
            _string(payload, "task_id"),
            _string(payload, "state"),
        )

    def cancel_run(self, *, run_id: str) -> PlatformRunRef:
        payload = self._call("runs.cancel", {"run_id": run_id}, idempotent=False)
        return PlatformRunRef(
            _string(payload, "run_id"),
            _string(payload, "task_id"),
            _string(payload, "state"),
        )

    def list_capabilities(self, *, agent_id: str) -> Sequence[CapabilityRef]:
        return tuple(
            CapabilityRef(_string(item, "capability_id"))
            for item in _sequence(
                self._call("capabilities.list", {"agent_id": agent_id}, idempotent=True),
                "capabilities",
            )
        )

    def request_approval(self, *, run_id: str, action: str) -> ApprovalRef:
        payload = self._call(
            "approvals.request",
            {"run_id": run_id, "action": action},
            idempotent=False,
        )
        return ApprovalRef(_string(payload, "approval_id"))

    def get_events(self, *, run_id: str) -> Sequence[Event]:
        events: list[Event] = []
        items = _sequence(
            self._call("runs.events", {"run_id": run_id}, idempotent=True),
            "events",
        )
        for item in items:
            occurred_at = _string(item, "occurred_at")
            try:
                parsed_at = datetime.fromisoformat(occurred_at.replace("Z", "+00:00"))
            except ValueError as exc:
                raise PlatformProtocolError(\n                    "event occurred_at is not a valid ISO-8601 timestamp"\n                ) from exc
            events.append(
                Event(
                    _string(item, "event_id"),
                    _string(item, "event_type"),
                    parsed_at,
                    _string(item, "workspace_id"),
                    item.get("session_id") if isinstance(item.get("session_id"), str) else None,
                    item.get("task_id") if isinstance(item.get("task_id"), str) else None,
                    item.get("agent_id") if isinstance(item.get("agent_id"), str) else None,
                    item.get("platform_run_id")\n                    if isinstance(item.get("platform_run_id"), str)\n                    else run_id,
                    _string(item, "correlation_id"),
                    "agent-platform",
                    item.get("payload") if isinstance(item.get("payload"), dict) else {},
                )
            )
        return tuple(events)

    def get_evidence(self, *, run_id: str) -> Sequence[EvidenceRef]:
        return tuple(
            EvidenceRef(_string(item, "evidence_id"))
            for item in _sequence(
                self._call("runs.evidence", {"run_id": run_id}, idempotent=True),
                "evidence",
            )
        )

    def health(self) -> bool:
        payload = self._call("health", {}, idempotent=True)
        return payload.get("ready") is True
