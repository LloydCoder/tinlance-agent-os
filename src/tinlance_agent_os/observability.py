"""OpenTelemetry instrumentation for Tinlance Agent OS."""

from __future__ import annotations

from collections.abc import Iterator, Mapping
from importlib import import_module
from contextlib import contextmanager
import os
from time import monotonic
from opentelemetry import metrics, propagate, trace
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.context import Context
from opentelemetry.trace import Span, Status, StatusCode


class AgentOSTelemetry:
    """Thin instrumentation facade over the OpenTelemetry API."""

    def __init__(self, name: str = "tinlance.agent.os") -> None:
        self.name = name
        self.tracer = trace.get_tracer(name)
        self.meter = metrics.get_meter(name)
        self.agent_uptime = self.meter.create_gauge(
            "agentos.agent.uptime",
            unit="s",
            description="Current observed agent uptime.",
        )
        self.task_latency = self.meter.create_histogram(
            "agentos.task.duration",
            unit="s",
            description="Task lifecycle duration.",
        )
        self.workflow_latency = self.meter.create_histogram(
            "agentos.workflow.duration",
            unit="s",
            description="Workflow lifecycle duration.",
        )
        self.model_latency = self.meter.create_histogram(
            "agentos.model.duration",
            unit="s",
            description="Model operation duration.",
        )
        self.tool_calls = self.meter.create_counter(
            "agentos.tool.calls",
            unit="1",
            description="Tool calls initiated by Agent OS.",
        )
        self.model_input_tokens = self.meter.create_counter(
            "gen_ai.usage.input_tokens",
            unit="{token}",
            description="Generative AI input token usage.",
        )
        self.model_output_tokens = self.meter.create_counter(
            "gen_ai.usage.output_tokens",
            unit="{token}",
            description="Generative AI output token usage.",
        )
        self.approval_latency = self.meter.create_histogram(
            "agentos.approval.duration",
            unit="s",
            description="Approval gate duration.",
        )
        self.retry_count = self.meter.create_counter(
            "agentos.retry.count",
            unit="1",
            description="Workflow and runtime retries.",
        )
        self.failure_count = self.meter.create_counter(
            "agentos.failure.count",
            unit="1",
            description="Observed OS operation failures.",
        )
        self.memory_operations = self.meter.create_counter(
            "agentos.memory.operations",
            unit="1",
            description="Memory operations.",
        )
        self.queue_depth = self.meter.create_up_down_counter(
            "agentos.queue.depth",
            unit="1",
            description="Current runtime queue depth delta.",
        )
        self.recovery_count = self.meter.create_counter(
            "agentos.recovery.count",
            unit="1",
            description="Recovered runtime operations.",
        )
        self.model_cost = self.meter.create_counter(
            "agentos.model.cost",
            unit="{USD}",
            description="Estimated model cost in USD.",
        )

    @contextmanager
    def span(
        self,
        name: str,
        attributes: Mapping[str, object] | None = None,
        *,
        context: Context | None = None,
    ) -> Iterator[Span]:
        start = monotonic()
        with self.tracer.start_as_current_span(name, context=context) as span:
            if attributes:
                self.set_attributes(span, attributes)
            try:
                yield span
            except Exception as exc:
                span.record_exception(exc)
                span.set_status(Status(StatusCode.ERROR, str(exc)))
                self.failure_count.add(1, {"operation.name": name})
                raise
            finally:
                span.set_attribute("agentos.operation.duration", monotonic() - start)

    @staticmethod
    def set_attributes(span: Span, attributes: Mapping[str, object]) -> None:
        for key, value in attributes.items():
            if value is None:
                continue
            if isinstance(value, (str, bool, int, float)):
                span.set_attribute(key, value)

    def record_agent_uptime(self, duration: float, *, agent_id: str) -> None:
        self.agent_uptime.set(duration, {"gen_ai.agent.id": agent_id})

    def record_task(self, duration: float, *, state: str) -> None:
        self.task_latency.record(duration, {"task.state": state})

    def record_workflow(self, duration: float, *, state: str) -> None:
        self.workflow_latency.record(duration, {"workflow.state": state})

    def record_model(
        self,
        duration: float,
        *,
        operation: str,
        model: str | None = None,
        provider: str | None = None,
        input_tokens: int | None = None,
        output_tokens: int | None = None,
        cost_usd: float | None = None,
    ) -> None:
        attrs: dict[str, object] = {"gen_ai.operation.name": operation}
        if model:
            attrs["gen_ai.request.model"] = model
        if provider:
            attrs["gen_ai.provider.name"] = provider
        self.model_latency.record(duration, attrs)
        if input_tokens is not None:
            self.model_input_tokens.add(input_tokens, attrs)
        if output_tokens is not None:
            self.model_output_tokens.add(output_tokens, attrs)
        if cost_usd is not None:
            self.model_cost.add(cost_usd, attrs)

    def record_tool(self, *, name: str, tool_type: str | None = None) -> None:
        attrs = {"gen_ai.tool.name": name}
        if tool_type:
            attrs["gen_ai.tool.type"] = tool_type
        self.tool_calls.add(1, attrs)

    def record_approval(self, duration: float, *, state: str) -> None:
        self.approval_latency.record(duration, {"approval.state": state})

    def record_retry(self, *, operation: str) -> None:
        self.retry_count.add(1, {"operation.name": operation})

    def record_memory(self, *, operation: str, scope: str) -> None:
        self.memory_operations.add(1, {"memory.operation": operation, "memory.scope": scope})

    def record_recovery(self, *, operation: str) -> None:
        self.recovery_count.add(1, {"operation.name": operation})


_default = AgentOSTelemetry()


def telemetry() -> AgentOSTelemetry:
    return _default


def configure_telemetry(
    *,
    service_name: str = "tinlance-agent-os",
    service_version: str = "0.1.0",
    endpoint: str | None = None,
) -> AgentOSTelemetry:
    """Configure process-wide OTLP tracing and metrics."""
    otlp_endpoint = endpoint or os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT")
    resource = Resource.create(
        {
            "service.name": service_name,
            "service.version": service_version,
            "service.namespace": "tinlance",
        }
    )
    tracer_provider = TracerProvider(resource=resource)
    if otlp_endpoint:
        metric_module = import_module("opentelemetry.exporter.otlp.proto.http.metric_exporter")
        trace_module = import_module("opentelemetry.exporter.otlp.proto.http.trace_exporter")
        metric_exporter = metric_module.OTLPMetricExporter(endpoint=otlp_endpoint)
        span_exporter = trace_module.OTLPSpanExporter(endpoint=otlp_endpoint)
        tracer_provider.add_span_processor(BatchSpanProcessor(span_exporter))
        metric_reader = PeriodicExportingMetricReader(metric_exporter)
        meter_provider = MeterProvider(resource=resource, metric_readers=[metric_reader])
    else:
        meter_provider = MeterProvider(resource=resource)
    trace.set_tracer_provider(tracer_provider)
    metrics.set_meter_provider(meter_provider)
    return AgentOSTelemetry(service_name)


def extract_trace_context(traceparent: str | None) -> Context | None:
    """Extract a W3C trace context from an untrusted inbound traceparent."""
    if not traceparent:
        return None
    return propagate.extract({"traceparent": traceparent})
