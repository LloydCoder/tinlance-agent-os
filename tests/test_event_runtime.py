from pathlib import Path

import pytest

from tinlance_agent_os.event_runtime import (
    DeliveryState,
    EventRuntimeError,
    EventSignalRuntime,
)


def runtime(tmp_path: Path) -> EventSignalRuntime:
    return EventSignalRuntime(tmp_path / "events.db")


def test_publish_is_deduplicated_and_delivers_to_matching_subscribers(tmp_path: Path) -> None:
    rt = runtime(tmp_path)
    sub = rt.subscribe(
        workspace_id="ws-1",
        event_type="task.completed",
        consumer_id="scheduler",
    )
    first = rt.publish(
        workspace_id="ws-1",
        event_type="task.completed",
        payload={"task": "t1"},
        correlation_id="corr-1",
        dedupe_key="task:t1:completed",
    )
    second = rt.publish(
        workspace_id="ws-1",
        event_type="task.completed",
        payload={"task": "t1"},
        correlation_id="corr-1",
        dedupe_key="task:t1:completed",
    )
    assert first.event_id == second.event_id
    pending = rt.pending("ws-1")
    assert pending == (pending[0],)
    assert pending[0].subscription_id == sub.subscription_id
    rt.acknowledge(first.event_id, sub.subscription_id)
    assert rt.pending("ws-1") == ()


def test_rejection_dead_letters_after_max_attempts_and_replay_recovers(tmp_path: Path) -> None:
    rt = runtime(tmp_path)
    sub = rt.subscribe(
        workspace_id="ws-1",
        event_type="signal",
        consumer_id="worker",
        max_attempts=2,
    )
    event = rt.publish(
        workspace_id="ws-1",
        event_type="signal",
        payload={"x": 1},
        correlation_id="c",
        dedupe_key="d",
    )
    assert rt.reject(event.event_id, sub.subscription_id) is DeliveryState.PENDING
    assert rt.reject(event.event_id, sub.subscription_id) is DeliveryState.DEAD_LETTER
    assert rt.replay("ws-1") == 1
    assert rt.pending("ws-1")[0].attempt == 2


def test_cross_workspace_events_are_isolated(tmp_path: Path) -> None:
    rt = runtime(tmp_path)
    rt.subscribe(workspace_id="ws-2", event_type="*", consumer_id="worker")
    rt.publish(
        workspace_id="ws-1",
        event_type="signal",
        payload={},
        correlation_id="c",
        dedupe_key="d",
    )
    assert rt.pending("ws-2") == ()


def test_invalid_attempt_limit_is_rejected(tmp_path: Path) -> None:
    rt = runtime(tmp_path)
    with pytest.raises(EventRuntimeError, match="max_attempts"):
        rt.subscribe(
            workspace_id="ws-1",
            event_type="signal",
            consumer_id="worker",
            max_attempts=0,
        )
