import pytest

from tinlance_agent_os.trace_context import TraceEvidenceRef, TraceLineageContext


def make_context(**overrides):
    values = {
        "trace_id": "4bf92f3577b34da6a3ce929d0e0e4736",
        "span_id": "00f067aa0ba902b7",
        "correlation_id": "corr-1",
        "request_id": "req-1",
        "tenant_id": "tenant-a",
        "workspace_id": "workspace-a",
        "execution_id": "run-1",
        "operation": "os.task.lifecycle",
        "started_at": "2026-10-18T05:00:00Z",
    }
    values.update(overrides)
    return TraceLineageContext(**values)


def test_os_child_span_preserves_tenant_and_execution_lineage():
    child = make_context().child(
        span_id="1111111111111111",
        operation="os.event.publish",
        started_at="2026-10-18T05:00:01Z",
    )
    payload = child.as_payload()
    assert payload["trace_id"] == "4bf92f3577b34da6a3ce929d0e0e4736"
    assert payload["parent_span_id"] == "00f067aa0ba902b7"
    assert payload["tenant_id"] == "tenant-a"
    assert payload["workspace_id"] == "workspace-a"
    assert payload["execution_id"] == "run-1"
    assert child.as_headers()["traceparent"] == (
        "00-4bf92f3577b34da6a3ce929d0e0e4736-1111111111111111-00"
    )


def test_os_trace_lineage_records_digest_not_raw_evidence():
    evidence = TraceEvidenceRef(evidence_id="evidence:1", kind="event", sha256="b" * 64)
    payload = make_context(evidence_refs=(evidence,)).as_payload()
    assert payload["evidence_refs"][0]["sha256"] == "b" * 64
    assert "raw_payload" not in payload


@pytest.mark.parametrize(
    "overrides",
    [
        {"trace_id": "0" * 32},
        {"span_id": "0" * 16},
        {"parent_span_id": "bad"},
        {"started_at": "2026-10-18T05:00:00"},
        {"safe_attributes": (("password", "secret"),)},
    ],
)
def test_os_trace_context_rejects_invalid_or_sensitive_metadata(overrides):
    with pytest.raises(ValueError):
        make_context(**overrides)
