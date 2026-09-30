from __future__ import annotations

from pathlib import Path

import pytest

from tinlance_agent_os.coordination import (
    AgentPrincipal,
    AgentTaskState,
    CoordinationError,
    HMACMessageAuthenticator,
    MultiAgentRuntime,
)
from tinlance_agent_os.store import StateStore


class CapabilityVerifier:
    def verify_delegation(self, *, supervisor, child_agent_id, requested_capabilities):
        return requested_capabilities


def setup(tmp_path: Path):
    store = StateStore(tmp_path / "state.db")
    store.upsert_workspace("ws", "owner", "2026-01-01T00:00:00+00:00")
    return store, MultiAgentRuntime(
        store,
        authenticator=HMACMessageAuthenticator({"default": b"secret"}),
        capability_verifier=CapabilityVerifier(),
    )


def principal(agent_id: str, caps=frozenset({"research.read"})) -> AgentPrincipal:
    return AgentPrincipal(agent_id, "ws", "tenant-1", True, caps)


def test_authenticated_delegation_preserves_identity_tenant_and_trace(tmp_path):
    store, runtime = setup(tmp_path)
    supervisor = principal("supervisor")
    child = principal("child")
    root = runtime.create_supervisor_task(supervisor, task_id="root", intent="supervise")
    result = runtime.delegate(
        supervisor,
        parent_task_id=root.task_id,
        child_agent=child,
        child_task_id="child-task",
        intent="research",
        requested_capabilities=frozenset({"research.read"}),
    )
    assert result.child_task.owner_agent_id == "child"
    assert result.child_task.parent_task_id == "root"
    assert result.child_task.trace_id == root.trace_id
    assert result.message.tenant_id == "tenant-1"
    assert store.get_agent_task("child-task")["tenant_id"] == "tenant-1"


def test_message_signature_and_payload_provenance_are_verified(tmp_path):
    _, runtime = setup(tmp_path)
    sender = principal("sender")
    recipient = principal("recipient")
    root = runtime.create_supervisor_task(sender, task_id="root", intent="send")
    message = runtime.send(
        sender,
        recipient_agent=recipient,
        parent_task_id=root.task_id,
        trace_id=root.trace_id,
        payload={"result": "ok"},
    )
    assert runtime.receive(message, expected_recipient=recipient) == message
    tampered = message.__class__(
        **{**message.__dict__, "payload": {"result": "forged"}}
    ) if hasattr(message, "__dict__") else None
    if tampered is not None:
        with pytest.raises(CoordinationError, match="digest"):
            runtime.receive(tampered, expected_recipient=recipient)


def test_spoofed_signature_is_rejected(tmp_path):
    _, runtime = setup(tmp_path)
    sender = principal("sender")
    recipient = principal("recipient")
    root = runtime.create_supervisor_task(sender, task_id="root", intent="send")
    message = runtime.send(
        sender,
        recipient_agent=recipient,
        parent_task_id=root.task_id,
        trace_id=root.trace_id,
        payload={"x": 1},
    )
    forged = message.__class__(
        message_id=message.message_id,
        workspace_id=message.workspace_id,
        tenant_id=message.tenant_id,
        sender_agent_id="attacker",
        recipient_agent_id=message.recipient_agent_id,
        parent_task_id=message.parent_task_id,
        trace_id=message.trace_id,
        sequence=message.sequence,
        nonce=message.nonce,
        payload=message.payload,
        payload_digest=message.payload_digest,
        signature=message.signature,
        key_id=message.key_id,
    )
    with pytest.raises(CoordinationError):
        runtime.receive(forged, expected_recipient=recipient)


def test_cross_tenant_and_cross_workspace_delegation_rejected(tmp_path):
    store, runtime = setup(tmp_path)
    supervisor = principal("supervisor")
    child = AgentPrincipal("child", "ws", "tenant-2", True, supervisor.capabilities)
    root = runtime.create_supervisor_task(supervisor, task_id="root", intent="supervise")
    with pytest.raises(CoordinationError, match="tenant"):
        runtime.delegate(
            supervisor,
            parent_task_id=root.task_id,
            child_agent=child,
            child_task_id="child",
            intent="research",
        )
    other = AgentPrincipal("other", "other-ws", "tenant-1", True, supervisor.capabilities)
    with pytest.raises(CoordinationError, match="workspace"):
        runtime.delegate(
            supervisor,
            parent_task_id=root.task_id,
            child_agent=other,
            child_task_id="child-2",
            intent="research",
        )


def test_capability_escalation_is_rejected(tmp_path):
    _, runtime = setup(tmp_path)
    supervisor = principal("supervisor", frozenset({"research.read"}))
    child = principal("child")
    root = runtime.create_supervisor_task(supervisor, task_id="root", intent="supervise")
    with pytest.raises(CoordinationError, match="exceeds"):
        runtime.delegate(
            supervisor,
            parent_task_id=root.task_id,
            child_agent=child,
            child_task_id="child",
            intent="research",
            requested_capabilities=frozenset({"admin.execute"}),
        )


def test_result_aggregation_and_tree_cancellation_preserve_tenant(tmp_path):
    _, runtime = setup(tmp_path)
    supervisor = principal("supervisor")
    child = principal("child")
    root = runtime.create_supervisor_task(supervisor, task_id="root", intent="supervise")
    first = runtime.delegate(
        supervisor,
        parent_task_id=root.task_id,
        child_agent=child,
        child_task_id="child-1",
        intent="one",
    )
    second = runtime.delegate(
        supervisor,
        parent_task_id=root.task_id,
        child_agent=child,
        child_task_id="child-2",
        intent="two",
    )
    rows = runtime.aggregate(supervisor, (first.child_task.task_id, second.child_task.task_id))
    assert {row.owner_agent_id for row in rows} == {"child"}
    cancelled = runtime.cancel_tree(supervisor, "root")
    assert set(cancelled) == {"root", "child-1", "child-2"}
    assert runtime.store.get_agent_task("child-1")["state"] == AgentTaskState.CANCELLED.value


def test_unauthenticated_identity_fails_closed(tmp_path):
    _, runtime = setup(tmp_path)
    with pytest.raises(CoordinationError, match="authenticated"):
        runtime.create_supervisor_task(
            AgentPrincipal("agent", "ws", "tenant-1", False),
            task_id="root",
            intent="x",
        )


def test_message_sequence_is_monotonic(tmp_path):
    _, runtime = setup(tmp_path)
    sender = principal("sender")
    recipient = principal("recipient")
    root = runtime.create_supervisor_task(sender, task_id="root", intent="send")
    first = runtime.send(sender, recipient_agent=recipient, parent_task_id="root", trace_id=root.trace_id, payload={"n": 1})
    second = runtime.send(sender, recipient_agent=recipient, parent_task_id="root", trace_id=root.trace_id, payload={"n": 2})
    assert (first.sequence, second.sequence) == (1, 2)
