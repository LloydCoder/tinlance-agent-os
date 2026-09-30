from __future__ import annotations

from opentelemetry import metrics, trace
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import InMemoryMetricReader
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import (
    InMemorySpanExporter,
    SimpleSpanProcessor,
)

from tinlance_agent_os.observability import AgentOSTelemetry


def test_opentelemetry_spans_and_metrics_are_emitted() -> None:
    span_exporter = InMemorySpanExporter()
    tracer_provider = TracerProvider()
    tracer_provider.add_span_processor(SimpleSpanProcessor(span_exporter))
    trace.set_tracer_provider(tracer_provider)

    metric_reader = InMemoryMetricReader()
    metrics.set_meter_provider(MeterProvider(metric_readers=[metric_reader]))

    telemetry = AgentOSTelemetry("tinlance.agent.os.test")
    with telemetry.span(
        "agentos.task",
        {
            "agentos.task.id": "task-1",
            "gen_ai.agent.id": "agent-1",
            "gen_ai.conversation.id": "session-1",
        },
    ), telemetry.span(
        "gen_ai.invoke",
        {
            "gen_ai.operation.name": "invoke_agent",
            "gen_ai.request.model": "model-1",
            "gen_ai.provider.name": "provider-1",
        },
    ):
        telemetry.record_model(
                0.25,
                operation="chat",
                model="model-1",
                provider="provider-1",
                input_tokens=10,
                output_tokens=20,
            )
            telemetry.record_tool(name="search", tool_type="function")
            telemetry.record_memory(operation="search", scope="session")
            telemetry.record_retry(operation="workflow.step")

    spans = span_exporter.get_finished_spans()
    assert [span.name for span in spans] == ["gen_ai.invoke", "agentos.task"]
    assert spans[0].attributes["gen_ai.request.model"] == "model-1"
    assert spans[1].attributes["gen_ai.conversation.id"] == "session-1"
    assert "gen_ai.input.messages" not in spans[0].attributes
    assert "gen_ai.output.messages" not in spans[0].attributes

    data = metric_reader.get_metrics_data()
    names = {
        metric.name
        for resource_metrics in data.resource_metrics
        for scope_metrics in resource_metrics.scope_metrics
        for metric in scope_metrics.metrics
    }
    assert "agentos.model.duration" in names
    assert "gen_ai.usage.input_tokens" in names
    assert "gen_ai.usage.output_tokens" in names
    assert "agentos.tool.calls" in names
    assert "agentos.memory.operations" in names
    assert "agentos.retry.count" in names
