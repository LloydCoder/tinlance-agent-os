"""M17 multi-agent coordination runtime.

The coordinator provides durable delegation/message semantics while keeping
identity, capability authority and consequential execution in the Platform.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import secrets
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any, Protocol

from .store import StateStore


def _now() -> datetime:
    return datetime.now(UTC)


def _digest(value: object) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode()
    ).hexdigest()


class CoordinationError(RuntimeError):
    pass


class AgentTaskState(StrEnum):
    CREATED = "created"
    RUNNING = "running"
    WAITING = "waiting"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass(frozen=True, slots=True)
class AgentPrincipal:
    agent_id: str
    workspace_id: str
    tenant_id: str
    authenticated: bool
    capabilities: frozenset[str] = frozenset()

    def validate(self) -> None:
        if not self.authenticated:
            raise CoordinationError("agent identity is not authenticated")
        if not self.agent_id or not self.workspace_id or not self.tenant_id:
            raise CoordinationError("authenticated agent identity is incomplete")


class IdentityAuthenticator(Protocol):
    def authenticate(
        self, *, agent_id: str, workspace_id: str, credential: str
    ) -> AgentPrincipal: ...


class CapabilityVerifier(Protocol):
    def verify_delegation(
        self,
        *,
        supervisor: AgentPrincipal,
        child_agent_id: str,
        requested_capabilities: frozenset[str],
    ) -> frozenset[str]: ...


class MessageAuthenticator(Protocol):
    def sign(self, payload: bytes, key_id: str) -> str: ...
    def verify(self, payload: bytes, signature: str, key_id: str) -> bool: ...


class HMACMessageAuthenticator:
    def __init__(self, keys: dict[str, bytes]) -> None:
        self._keys = dict(keys)

    def sign(self, payload: bytes, key_id: str) -> str:
        key = self._keys.get(key_id)
        if key is None:
            raise CoordinationError("unknown message signing key")
        return hmac.new(key, payload, hashlib.sha256).hexdigest()

    def verify(self, payload: bytes, signature: str, key_id: str) -> bool:
        key = self._keys.get(key_id)
        if key is None:
            return False
        expected = hmac.new(key, payload, hashlib.sha256).hexdigest()
        return hmac.compare_digest(expected, signature)


@dataclass(frozen=True, slots=True)
class AgentTask:
    task_id: str
    workspace_id: str
    tenant_id: str
    owner_agent_id: str
    parent_task_id: str | None
    trace_id: str
    state: AgentTaskState
    delegated_capabilities: frozenset[str] = frozenset()


@dataclass(frozen=True, slots=True)
class AgentMessage:
    message_id: str
    workspace_id: str
    tenant_id: str
    sender_agent_id: str
    recipient_agent_id: str
    parent_task_id: str
    trace_id: str
    sequence: int
    nonce: str
    payload: dict[str, Any]
    payload_digest: str
    signature: str
    key_id: str


@dataclass(frozen=True, slots=True)
class DelegationResult:
    child_task: AgentTask
    message: AgentMessage


class MultiAgentRuntime:
    def __init__(
        self,
        store: StateStore,
        *,
        authenticator: MessageAuthenticator,
        capability_verifier: CapabilityVerifier,
    ) -> None:
        self.store = store
        self.authenticator = authenticator
        self.capability_verifier = capability_verifier

    def authenticate(
        self,
        authenticator: IdentityAuthenticator,
        *,
        agent_id: str,
        workspace_id: str,
        credential: str,
    ) -> AgentPrincipal:
        principal = authenticator.authenticate(
            agent_id=agent_id, workspace_id=workspace_id, credential=credential
        )
        principal.validate()
        return principal

    def create_supervisor_task(
        self,
        principal: AgentPrincipal,
        *,
        task_id: str,
        intent: str,
        trace_id: str | None = None,
    ) -> AgentTask:
        principal.validate()
        trace = trace_id or secrets.token_hex(16)
        task = AgentTask(
            task_id=task_id,
            workspace_id=principal.workspace_id,
            tenant_id=principal.tenant_id,
            owner_agent_id=principal.agent_id,
            parent_task_id=None,
            trace_id=trace,
            state=AgentTaskState.CREATED,
        )
        self.store.create_agent_task(task, intent=intent)
        return task

    def delegate(
        self,
        supervisor: AgentPrincipal,
        *,
        parent_task_id: str,
        child_agent: AgentPrincipal,
        child_task_id: str,
        intent: str,
        requested_capabilities: frozenset[str] = frozenset(),
    ) -> DelegationResult:
        supervisor.validate()
        child_agent.validate()
        if supervisor.workspace_id != child_agent.workspace_id:
            raise CoordinationError("cross-workspace delegation is forbidden")
        if supervisor.tenant_id != child_agent.tenant_id:
            raise CoordinationError("cross-tenant delegation is forbidden")
        parent = self.store.get_agent_task(parent_task_id)
        if parent is None:
            raise CoordinationError("parent task not found")
        if parent["owner_agent_id"] != supervisor.agent_id:
            raise CoordinationError("supervisor does not own parent task")
        if parent["tenant_id"] != supervisor.tenant_id:
            raise CoordinationError("parent task tenant mismatch")
        granted = self.capability_verifier.verify_delegation(
            supervisor=supervisor,
            child_agent_id=child_agent.agent_id,
            requested_capabilities=requested_capabilities,
        )
        if not granted <= supervisor.capabilities:
            raise CoordinationError("delegated capability exceeds supervisor authority")
        child = AgentTask(
            task_id=child_task_id,
            workspace_id=supervisor.workspace_id,
            tenant_id=supervisor.tenant_id,
            owner_agent_id=child_agent.agent_id,
            parent_task_id=parent_task_id,
            trace_id=parent["trace_id"],
            state=AgentTaskState.CREATED,
            delegated_capabilities=granted,
        )
        self.store.create_agent_task(child, intent=intent)
        message = self.send(
            supervisor,
            recipient_agent=child_agent,
            parent_task_id=child_task_id,
            trace_id=child.trace_id,
            payload={"type": "delegation", "intent": intent, "task_id": child_task_id},
        )
        return DelegationResult(child, message)

    def send(
        self,
        sender: AgentPrincipal,
        *,
        recipient_agent: AgentPrincipal,
        parent_task_id: str,
        trace_id: str,
        payload: dict[str, Any],
        key_id: str = "default",
    ) -> AgentMessage:
        sender.validate()
        recipient_agent.validate()
        if sender.workspace_id != recipient_agent.workspace_id:
            raise CoordinationError("cross-workspace message rejected")
        if sender.tenant_id != recipient_agent.tenant_id:
            raise CoordinationError("cross-tenant message rejected")
        task = self.store.get_agent_task(parent_task_id)
        if task is None or task["tenant_id"] != sender.tenant_id:
            raise CoordinationError("message task is not in sender tenant")
        sequence = self.store.next_agent_message_sequence(parent_task_id)
        message_id = _digest(
            {
                "task": parent_task_id,
                "sender": sender.agent_id,
                "recipient": recipient_agent.agent_id,
                "sequence": sequence,
                "trace": trace_id,
            }
        )
        envelope = {
            "message_id": message_id,
            "workspace_id": sender.workspace_id,
            "tenant_id": sender.tenant_id,
            "sender_agent_id": sender.agent_id,
            "recipient_agent_id": recipient_agent.agent_id,
            "parent_task_id": parent_task_id,
            "trace_id": trace_id,
            "sequence": sequence,
            "nonce": secrets.token_hex(16),
            "payload": payload,
        }
        payload_digest = _digest(payload)
        envelope["payload_digest"] = payload_digest
        raw = json.dumps(envelope, sort_keys=True, separators=(",", ":")).encode()
        signature = self.authenticator.sign(raw, key_id)
        message = AgentMessage(
            message_id=message_id,
            workspace_id=sender.workspace_id,
            tenant_id=sender.tenant_id,
            sender_agent_id=sender.agent_id,
            recipient_agent_id=recipient_agent.agent_id,
            parent_task_id=parent_task_id,
            trace_id=trace_id,
            sequence=sequence,
            nonce=str(envelope["nonce"]),
            payload=payload,
            payload_digest=payload_digest,
            signature=signature,
            key_id=key_id,
        )
        self.store.append_agent_message(message)
        return message

    def receive(self, message: AgentMessage, *, expected_recipient: AgentPrincipal) -> AgentMessage:
        expected_recipient.validate()
        if message.recipient_agent_id != expected_recipient.agent_id:
            raise CoordinationError("message recipient mismatch")
        if message.workspace_id != expected_recipient.workspace_id:
            raise CoordinationError("message workspace mismatch")
        if message.tenant_id != expected_recipient.tenant_id:
            raise CoordinationError("message tenant mismatch")
        if _digest(message.payload) != message.payload_digest:
            raise CoordinationError("message payload digest mismatch")
        envelope = {
            "message_id": message.message_id,
            "workspace_id": message.workspace_id,
            "tenant_id": message.tenant_id,
            "sender_agent_id": message.sender_agent_id,
            "recipient_agent_id": message.recipient_agent_id,
            "parent_task_id": message.parent_task_id,
            "trace_id": message.trace_id,
            "sequence": message.sequence,
            "nonce": message.nonce,
            "payload": message.payload,
            "payload_digest": message.payload_digest,
        }
        raw = json.dumps(envelope, sort_keys=True, separators=(",", ":")).encode()
        if not self.authenticator.verify(raw, message.signature, message.key_id):
            raise CoordinationError("message signature verification failed")
        return message

    def aggregate(
        self, supervisor: AgentPrincipal, child_task_ids: tuple[str, ...]
    ) -> tuple[AgentTask, ...]:
        supervisor.validate()
        results: list[AgentTask] = []
        for task_id in child_task_ids:
            row = self.store.get_agent_task(task_id)
            if row is None:
                raise CoordinationError("child task not found")
            if row["tenant_id"] != supervisor.tenant_id:
                raise CoordinationError("cross-tenant result aggregation rejected")
            if row["parent_task_id"] is None:
                raise CoordinationError("task is not a child task")
            parent = self.store.get_agent_task(row["parent_task_id"])
            if parent is None or parent["owner_agent_id"] != supervisor.agent_id:
                raise CoordinationError("supervisor does not own child task")
            results.append(
                AgentTask(
                    row["task_id"],
                    row["workspace_id"],
                    row["tenant_id"],
                    row["owner_agent_id"],
                    row["parent_task_id"],
                    row["trace_id"],
                    AgentTaskState(row["state"]),
                    frozenset(json.loads(row["delegated_capabilities"])),
                )
            )
        return tuple(results)

    def cancel_tree(self, supervisor: AgentPrincipal, root_task_id: str) -> tuple[str, ...]:
        supervisor.validate()
        root = self.store.get_agent_task(root_task_id)
        if root is None or root["owner_agent_id"] != supervisor.agent_id:
            raise CoordinationError("supervisor does not own root task")
        return self.store.cancel_agent_task_tree(root_task_id, supervisor.tenant_id)
