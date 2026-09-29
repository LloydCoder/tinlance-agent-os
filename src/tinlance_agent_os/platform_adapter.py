"""Concrete Agent Platform adapter for Agent OS."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, replace
import json
from datetime import datetime
from hashlib import sha256
from typing import cast

from .contracts import AgentPlatformClient
from .domain import Agent, ApprovalRef, CapabilityRef, Event, EvidenceRef, PlatformRunRef, User
from .errors import PlatformProtocolError
from .transport import PlatformRequestContext, PlatformTransport


def _string(payload: Mapping[str, object], key: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value:
        raise PlatformProtocolError(f"Platform payload field {key!r} must be a non-empty string")
    return value


def _optional_string(payload: Mapping[str, object], key: str) -> str | None:
    value = payload.get(key)
    return value if isinstance(value, str) else None


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
    """Maps OS operations to the versioned Platform API contract."""

    transport: PlatformTransport
    context: PlatformRequestContext

    @staticmethod
    def _stable_request_id(operation: str, payload: Mapping[str, object]) -> str:
        canonical = json.dumps(
            {"operation": operation, "payload": dict(payload)},
            sort_keys=True,
            separators=(",", ":"),
        )
        return sha256(canonical.encode("utf-8")).hexdigest()

    def _call(
        self,
        operation: str,
        payload: Mapping[str, object],
        *,
        idempotent: bool,
    ) -> Mapping[str, object]:
        request_context = replace(
            self.context,
            request_id=self._stable_request_id(operation, payload),
        )
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
        payload = self._call("agents.list", {}, idempotent=True)
        return tuple(
            Agent(
                _string(item, "agent_id"),
                _string(item, "name"),
                _string(item, "version"),
            )
            for item in _sequence(payload, "agents")
        )

    def create_run(self, *, task_id: str, agent_id: str, intent: str) -> PlatformRunRef:
        payload = self._call(
            "runs.create",
            {"task_id": task_id, "agent_id": agent_id, "intent": intent},
            idempotent=True,
        )
        return PlatformRunRef(
            _string(payload, "run_id"),
            _string(payload, "task_id"),
            _string(payload, "state"),
        )

    def cancel_run(self, *, run_id: str) -> PlatformRunRef:
        payload = self._call("runs.cancel", {"run_id": run_id}, idempotent=True)
        return PlatformRunRef(
            _string(payload, "run_id"),
            _string(payload, "task_id"),
            _string(payload, "state"),
        )

    def list_capabilities(self, *, agent_id: str) -> Sequence[CapabilityRef]:
        payload = self._call(
            "capabilities.list",
            {"agent_id": agent_id},
            idempotent=True,
        )
        return tuple(
            CapabilityRef(_string(item, "capability_id"))
            for item in _sequence(payload, "capabilities")
        )

    def request_approval(
        self,
        *,
        run_id: str,
        action: str,
        resource: str | None = None,
        reason: str | None = None,
    ) -> ApprovalRef:
        payload = self._call(
            "approvals.request",
            {
                "run_id": run_id,
                "action": action,
                "resource": resource or action,
                "reason": reason or "Agent OS requested governed approval",
            },
            idempotent=True,
        )
        return ApprovalRef(_string(payload, "approval_id"))

    def get_events(self, *, run_id: str) -> Sequence[Event]:
        payload = self._call("runs.events", {"run_id": run_id}, idempotent=True)
        items = _sequence(payload, "events")
        events: list[Event] = []
        for item in items:
            occurred_at = _string(item, "occurred_at")
            try:
                parsed_at = datetime.fromisoformat(occurred_at.replace("Z", "+00:00"))
            except ValueError as exc:
                raise PlatformProtocolError(
                    "event occurred_at is not a valid ISO-8601 timestamp"
                ) from exc
            session_id = _optional_string(item, "session_id")
            task_id = _optional_string(item, "task_id")
            agent_id = _optional_string(item, "agent_id")
            platform_run_id = item.get("platform_run_id")
            if not isinstance(platform_run_id, str):
                platform_run_id = run_id
            event_payload = item.get("payload")
            if not isinstance(event_payload, dict):
                event_payload = {}
            events.append(
                Event(
                    _string(item, "event_id"),
                    _string(item, "event_type"),
                    parsed_at,
                    _string(item, "workspace_id"),
                    session_id,
                    task_id,
                    agent_id,
                    platform_run_id,
                    _string(item, "correlation_id"),
                    "agent-platform",
                    event_payload,
                )
            )
        return tuple(events)

    def get_evidence(self, *, run_id: str) -> Sequence[EvidenceRef]:
        payload = self._call("runs.evidence", {"run_id": run_id}, idempotent=True)
        items = _sequence(payload, "evidence")
        return tuple(EvidenceRef(_string(item, "evidence_id")) for item in items)

    def health(self) -> bool:
        payload = self._call("health", {}, idempotent=True)
        return payload.get("ready") is True
