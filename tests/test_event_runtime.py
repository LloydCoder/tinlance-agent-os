import sqlite3
from datetime import UTC, datetime, timedelta
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
    assert (
        rt.claim_pending(
            tenant_id="tenant-a",
            workspace_id="ws-1",
            worker_id="worker-b",
        )
        == ()
    )
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
    assert (
        rt.reject(
            tenant_id="tenant-a",
            event_id=event.event_id,
            subscription_id=sub.subscription_id,
            worker_id="worker-a",
            lease_token=first.lease_token,
        )
        is DeliveryState.PENDING
    )
    second = claim(rt, sub)
    assert (
        rt.reject(
            tenant_id="tenant-a",
            event_id=event.event_id,
            subscription_id=sub.subscription_id,
            worker_id="worker-a",
            lease_token=second.lease_token,
        )
        is DeliveryState.DEAD_LETTER
    )
    assert rt.pending("tenant-a", "ws-1") == ()
    assert (
        rt.replay(
            tenant_id="tenant-a",
            workspace_id="ws-1",
            operator_id="operator-1",
            reason="replay after consumer fix",
        )
        == 1
    )
    assert rt.pending("tenant-a", "ws-1")[0].attempt == 0
    with sqlite3.connect(rt.path) as db:
        audit = db.execute(
            "SELECT operator_id,reason,replayed_count FROM os_event_replays_p3"
        ).fetchone()
    assert audit == ("operator-1", "replay after consumer fix", 1)


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


def test_event_is_durable_across_runtime_restart(tmp_path: Path) -> None:
    path = tmp_path / "restart.db"
    first_runtime = EventSignalRuntime(path, retry_base_seconds=0, retry_max_seconds=0)
    subscription = first_runtime.subscribe(
        tenant_id="tenant-a",
        workspace_id="ws-1",
        event_type="task.completed",
        consumer_id="scheduler",
    )
    event = first_runtime.publish(
        tenant_id="tenant-a",
        workspace_id="ws-1",
        event_type="task.completed",
        payload={"task": "t1"},
        correlation_id="corr-restart",
        dedupe_key="restart-task-completed",
    )
    reopened = EventSignalRuntime(path, retry_base_seconds=0, retry_max_seconds=0)
    delivery = claim(reopened, subscription)
    assert delivery.event_id == event.event_id
    reopened.acknowledge(
        tenant_id="tenant-a",
        event_id=event.event_id,
        subscription_id=subscription.subscription_id,
        worker_id="worker-a",
        lease_token=delivery.lease_token,
    )
    assert reopened.pending("tenant-a", "ws-1") == ()


def test_expired_lease_cannot_ack_and_can_be_reclaimed(tmp_path: Path) -> None:
    now = [datetime(2026, 10, 18, 4, 0, tzinfo=UTC)]
    rt = EventSignalRuntime(
        tmp_path / "lease-expiry.db",
        retry_base_seconds=0,
        retry_max_seconds=0,
        clock=lambda: now[0],
    )
    sub = subscribe(rt)
    event = publish(rt)
    first = rt.claim_pending(
        tenant_id="tenant-a", workspace_id="ws-1", worker_id="worker-a", lease_seconds=1
    )[0]
    now[0] += timedelta(seconds=2)
    with pytest.raises(EventRuntimeError, match="stale, unauthorized"):
        rt.acknowledge(
            tenant_id="tenant-a",
            event_id=event.event_id,
            subscription_id=sub.subscription_id,
            worker_id="worker-a",
            lease_token=first.lease_token,
        )
    second = rt.claim_pending(
        tenant_id="tenant-a", workspace_id="ws-1", worker_id="worker-b", lease_seconds=30
    )[0]
    assert second.lease_token != first.lease_token
    rt.acknowledge(
        tenant_id="tenant-a",
        event_id=event.event_id,
        subscription_id=sub.subscription_id,
        worker_id="worker-b",
        lease_token=second.lease_token,
    )


def test_returned_event_payload_is_recursively_immutable(tmp_path: Path) -> None:
    rt = runtime(tmp_path)
    original = {"nested": {"state": "succeeded"}}
    event = publish(rt, payload=original)
    original["nested"]["state"] = "failed"
    with pytest.raises(TypeError):
        event.payload["nested"]["state"] = "mutated"
    assert event.as_payload()["data"]["nested"]["state"] == "succeeded"


def test_event_runtime_persists_span_lineage_and_emits_span_id(tmp_path: Path) -> None:
    rt = runtime(tmp_path)
    span_id = "00f067aa0ba902b7"
    parent_span_id = "1111111111111111"
    event = publish(
        rt,
        trace_id="4bf92f3577b34da6a3ce929d0e0e4736",
        span_id=span_id,
        parent_span_id=parent_span_id,
    )
    assert event.span_id == span_id
    assert event.parent_span_id == parent_span_id
    assert event.as_payload()["spanid"] == span_id
    duplicate = publish(
        rt,
        trace_id="4bf92f3577b34da6a3ce929d0e0e4736",
        span_id="2222222222222222",
        parent_span_id=parent_span_id,
    )
    assert duplicate.event_id == event.event_id
    assert duplicate.span_id == span_id
    assert duplicate.parent_span_id == parent_span_id


def test_event_runtime_rejects_invalid_span_ids(tmp_path: Path) -> None:
    rt = runtime(tmp_path)
    with pytest.raises(EventRuntimeError, match="span_id"):
        publish(rt, span_id="0" * 16)
    with pytest.raises(EventRuntimeError, match="parent_span_id"):
        publish(rt, parent_span_id="not-a-span")


def test_replay_is_tenant_scoped_and_cannot_release_another_tenants_dead_letter(
    tmp_path: Path,
) -> None:
    rt = runtime(tmp_path)
    sub = subscribe(rt, tenant_id="tenant-a", workspace_id="ws-a", max_attempts=1)
    event = rt.publish(
        tenant_id="tenant-a",
        workspace_id="ws-a",
        event_type="task.completed",
        payload={"task": "private-a"},
        correlation_id="corr-a",
        dedupe_key="task:private-a:completed",
    )
    delivery = rt.claim_pending(
        tenant_id="tenant-a", workspace_id="ws-a", worker_id="worker-a", limit=1
    )[0]
    assert (
        rt.reject(
            tenant_id="tenant-a",
            event_id=event.event_id,
            subscription_id=sub.subscription_id,
            worker_id="worker-a",
            lease_token=delivery.lease_token,
        )
        is DeliveryState.DEAD_LETTER
    )

    assert (
        rt.replay(
            tenant_id="tenant-b",
            workspace_id="ws-a",
            operator_id="operator-b",
            reason="attempted cross-tenant recovery",
        )
        == 0
    )
    assert rt.pending("tenant-a", "ws-a") == ()
    assert (
        rt.replay(
            tenant_id="tenant-a",
            workspace_id="ws-a",
            operator_id="operator-a",
            reason="authorized tenant recovery",
        )
        == 1
    )
    assert len(rt.pending("tenant-a", "ws-a")) == 1
    assert rt.pending("tenant-b", "ws-a") == ()
