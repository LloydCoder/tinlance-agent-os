from pathlib import Path

import pytest

from tinlance_agent_os.event_runtime import (
    DeliveryState,
    EventRuntimeError,
    EventSignalRuntime,
)


def runtime(tmp_path: Path) -> EventSignalRuntime:
    return EventSignalRuntime(
        tmp_path / "events.db",
        retry_base_seconds=0,
        retry_max_seconds=0,
    )


def publish(rt, *, tenant_id="tenant-a", workspace_id="ws-1", payload=None, **kwargs):
    return rt.publish(
        tenant_id=tenant_id,
        workspace_id=workspace_id,
        event_type="task.completed",
        payload=payload or {"task": "t1"},
        correlation_id="corr-1",
        dedupe_key="task:t1:completed",
        **kwargs,
    )


def subscribe(rt, *, tenant_id="tenant-a", workspace_id="ws-1", max_attempts=3):
    return rt.subscribe(
        tenant_id=tenant_id,
        workspace_id=workspace_id,
        event_type="task.completed",
        consumer_id="scheduler",
        max_attempts=max_attempts,
    )


def claim(rt, sub, *, tenant_id="tenant-a", workspace_id="ws-1", worker="worker-a"):
    claimed = rt.claim_pending(
        tenant_id=tenant_id, workspace_id=workspace_id, worker_id=worker, limit=10
    )
    assert claimed
    return claimed[0]


def test_publish_is_deduplicated_and_uses_canonical_envelope(tmp_path: Path) -> None:
    rt = runtime(tmp_path)
    sub = subscribe(rt)
    first = publish(rt, trace_id="4bf92f3577b34da6a3ce929d0e0e4736")
    second = publish(rt, trace_id="4bf92f3577b34da6a3ce929d0e0e4736")
    assert first.event_id == second.event_id
    payload = first.as_payload()
    assert payload["specversion"] == "1.0"
    assert payload["datacontenttype"] == "application/json"
    assert payload["tenantid"] == "tenant-a"
    assert payload["traceid"] == "4bf92f3577b34da6a3ce929d0e0e4736"
    assert rt.pending("tenant-a", "ws-1")[0].subscription_id == sub.subscription_id
    delivery = claim(rt, sub)
    rt.acknowledge(
        tenant_id="tenant-a",
        event_id=first.event_id,
        subscription_id=sub.subscription_id,
        worker_id="worker-a",
        lease_token=delivery.lease_token,
    )
    assert rt.pending("tenant-a", "ws-1") == ()


def test_dedupe_key_conflict_is_rejected(tmp_path: Path) -> None:
    rt = runtime(tmp_path)
    publish(rt, payload={"task": "t1"})
    with pytest.raises(EventRuntimeError, match="conflicting event"):
        publish(rt, payload={"task": "different"})


def test_tenant_and_workspace_isolation(tmp_path: Path) -> None:
    rt = runtime(tmp_path)
    subscribe(rt, tenant_id="tenant-b", workspace_id="ws-2")
    publish(rt, tenant_id="tenant-a", workspace_id="ws-1")
    assert rt.pending("tenant-b", "ws-2") == ()
    assert rt.pending("tenant-a", "ws-2") == ()
    assert rt.pending("tenant-b", "ws-1") == ()


def test_delivery_lease_is_exclusive_and_ack_is_owner_bound(tmp_path: Path) -> None:
    rt = runtime(tmp_path)
    sub = subscribe(rt)
    event = publish(rt)
    lease = claim(rt, sub, worker="worker-a")
    assert rt.claim_pending(
        tenant_id="tenant-a",
        workspace_id="ws-1",
        worker_id="worker-b",
    ) == ()
    with pytest.raises(EventRuntimeError, match="stale, unauthorized"):
        rt.acknowledge(
            tenant_id="tenant-a",
            event_id=event.event_id,
            subscription_id=sub.subscription_id,
            worker_id="worker-b",
            lease_token=lease.lease_token,
        )
    rt.acknowledge(
        tenant_id="tenant-a",
        event_id=event.event_id,
        subscription_id=sub.subscription_id,
        worker_id="worker-a",
        lease_token=lease.lease_token,
    )


def test_rejection_dead_letters_after_max_attempts_and_replay_is_audited(tmp_path: Path) -> None:
    rt = runtime(tmp_path)
    sub = subscribe(rt, max_attempts=2)
    event = publish(rt)
    first = claim(rt, sub)
    assert rt.reject(
        tenant_id="tenant-a",
        event_id=event.event_id,
        subscription_id=sub.subscription_id,
        worker_id="worker-a",
        lease_token=first.lease_token,
    ) is DeliveryState.PENDING
    second = claim(rt, sub)
    assert rt.reject(
        tenant_id="tenant-a",
        event_id=event.event_id,
        subscription_id=sub.subscription_id,
        worker_id="worker-a",
        lease_token=second.lease_token,
    ) is DeliveryState.DEAD_LETTER
    assert rt.pending("tenant-a", "ws-1") == ()
    assert rt.replay(
        tenant_id="tenant-a",
        workspace_id="ws-1",
        operator_id="operator-1",
        reason="replay after consumer fix",
    ) == 1
    assert rt.pending("tenant-a", "ws-1")[0].attempt == 0


def test_invalid_attempt_limit_and_trace_id_are_rejected(tmp_path: Path) -> None:
    rt = runtime(tmp_path)
    with pytest.raises(EventRuntimeError, match="max_attempts"):
        subscribe(rt, max_attempts=0)
    with pytest.raises(EventRuntimeError, match="trace_id"):
        publish(rt, trace_id="0" * 32)


def test_payload_size_and_json_values_are_bounded(tmp_path: Path) -> None:
    rt = runtime(tmp_path)
    with pytest.raises(EventRuntimeError, match="finite JSON"):
        publish(rt, payload={"nan": float("nan")})
    with pytest.raises(EventRuntimeError, match="1 MiB"):
        publish(rt, payload={"blob": "x" * (1_100_000)})


def test_replay_requires_audit_reason(tmp_path: Path) -> None:
    rt = runtime(tmp_path)
    with pytest.raises(EventRuntimeError, match="reason"):
        rt.replay(tenant_id="tenant-a", workspace_id="ws-1", operator_id="operator-1", reason=" ")
