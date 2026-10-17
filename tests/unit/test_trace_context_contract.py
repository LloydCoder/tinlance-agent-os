import pytest

from tinlance_agent_os.transport import PlatformRequestContext


def test_context_accepts_matching_w3c_trace_fields() -> None:
    trace_id = "a" * 32
    span_id = "b" * 16
    header = f"00-{trace_id}-{span_id}-01"
    context = PlatformRequestContext(
        "tenant-1",
        "subject-1",
        "request-1",
        trace_id=trace_id,
        span_id=span_id,
        traceparent=header,
    )
    assert context.trace_id == trace_id
    assert context.span_id == span_id
    assert context.traceparent == header


def test_context_rejects_mismatched_w3c_trace_fields() -> None:
    with pytest.raises(ValueError):
        PlatformRequestContext(
            "tenant-1",
            "subject-1",
            "request-1",
            trace_id="a" * 32,
            span_id="c" * 16,
            traceparent=f"00-{'a' * 32}-{'b' * 16}-01",
        )
