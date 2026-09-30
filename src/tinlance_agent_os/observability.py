"""OpenTelemetry instrumentation for Tinlance Agent OS."""

from __future__ import annotations

from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from time import monotonic
from opentelemetry import metrics, trace
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

    @contextmanager
    def span(
        self,
        name: str,
        attributes: Mapping[str, object] | None = None,
    ) -> Iterator[Span]:
        start = monotonic()
        with self.tracer.start_as_current_span(name) as span:
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
