from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from tinlance_agent_os.resource import ResourceLedger, UsageRecord
from tinlance_agent_os.store import StateStore


def make_ledger(tmp_path: Path) -> ResourceLedger:
    store = StateStore(tmp_path / "state.db")
    store.upsert_workspace("workspace-1", "user-1", "2026-10-03T00:00:00+00:00")
    return ResourceLedger(store)


def test_usage_is_durable_and_attributable(tmp_path: Path) -> None:
    ledger = make_ledger(tmp_path)
    ledger.record(
        UsageRecord(
            "u1",
            "workspace-1",
            "model_tokens",
            1000,
            "tokens",
            2500,
            agent_id="agent-1",
            task_id="task-1",
            model="model-a",
            provider="provider-a",
            occurred_at=datetime(2026, 10, 3, tzinfo=UTC),
        )
    )
    ledger.record(
        UsageRecord(
            "u2",
            "workspace-1",
            "model_tokens",
            500,
            "tokens",
            1250,
            agent_id="agent-2",
        )
    )
    assert ledger.summarize("workspace-1")[0].quantity == 1500
    assert ledger.attributable_cost_micros("workspace-1", agent_id="agent-1") == 2500


def test_negative_usage_and_naive_timestamps_fail_closed(tmp_path: Path) -> None:
    ledger = make_ledger(tmp_path)
    with pytest.raises(ValueError, match="non-negative"):
        ledger.record(UsageRecord("u1", "workspace-1", "cpu", -1, "ms"))
    with pytest.raises(ValueError, match="timezone-aware"):
        ledger.record(
            UsageRecord(
                "u2",
                "workspace-1",
                "cpu",
                1,
                "ms",
                occurred_at=datetime(2026, 10, 3),
            )
        )


def test_duplicate_usage_id_is_rejected(tmp_path: Path) -> None:
    ledger = make_ledger(tmp_path)
    record = UsageRecord("u1", "workspace-1", "storage", 1, "bytes")
    ledger.record(record)
    with pytest.raises(sqlite3.IntegrityError):
        ledger.record(record)
