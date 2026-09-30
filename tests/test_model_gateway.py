import pytest

from __future__ import annotations

from tinlance_agent_os import (
    ModelCapabilities,
    ModelDescriptor,
    ModelGateway,
    ModelRegistry,
    ModelRequest,
    ModelPricing,
    ModelRouter,
    ModelResponse,
    ModelRoutingError,
    ModelTask,
    ModelUsage,
    PrivacyLevel,
    ProviderUnavailable,
    RerankInput,
    RerankItem,
    RoutingPolicy,
)
from tinlance_agent_os.sdk import AgentSDK, ExecutionContext, TraceContext
from tinlance_agent_os.client import ReferenceAgentPlatformClient
from tinlance_agent_os.domain import User
from tinlance_agent_os.store import StateStore


class FakeProvider:
    def __init__(self, provider_id: str, *, fail: bool = False) -> None:
        self.provider_id = provider_id
        self.fail = fail
        self.calls = 0

    def health(self) -> bool:
        return True

    def complete(self, request: ModelRequest, model: ModelDescriptor) -> ModelResponse:
        self.calls += 1
        if self.fail:
            raise ProviderUnavailable("temporary outage")
        return ModelResponse(
            task=request.task,
            model_id=model.model_id,
            provider_id=self.provider_id,
            output=f"{self.provider_id}:{model.model_id}",
            usage=ModelUsage(10, 5, 15),
        )

    def embed(self, request: ModelRequest, model: ModelDescriptor) -> ModelResponse:
        self.calls += 1
        return ModelResponse(
            task=request.task,
            model_id=model.model_id,
            provider_id=self.provider_id,
            output=(0.1, 0.2, 0.3),
            usage=ModelUsage(3, 0, 3),
        )

    def rerank(self, request: ModelRequest, model: ModelDescriptor) -> ModelResponse:
        self.calls += 1
        payload = request.payload
        assert isinstance(payload, RerankInput)
        return ModelResponse(
            task=request.task,
            model_id=model.model_id,
            provider_id=self.provider_id,
            output=tuple(
                RerankItem(index=index, score=1.0 - index / 10, document=document)
                for index, document in enumerate(payload.documents)
            ),
            usage=ModelUsage(5, 0, 5),
        )


def descriptor(
    model_id: str,
    provider_id: str,
    *,
    privacy: PrivacyLevel = PrivacyLevel.PUBLIC,
    tasks: frozenset[ModelTask] | None = None,
    context_window: int = 8192,
    input_price: float | None = 1.0,
    output_price: float | None = 2.0,
    latency: int | None = 100,
    features: frozenset[str] = frozenset(),
) -> ModelDescriptor:
    return ModelDescriptor(
        model_id=model_id,
        provider_id=provider_id,
        capabilities=ModelCapabilities(
            tasks=tasks or frozenset({ModelTask.CHAT, ModelTask.DECISION}),
            context_window=context_window,
            features=features,
            structured_output=True,
        ),
        privacy=privacy,
        pricing=ModelPricing(
            input_usd_per_million=input_price,
            output_usd_per_million=output_price,
        ),
        estimated_latency_ms=latency,
    )


def test_router_matches_capability_cost_latency_context_and_privacy() -> None:
    registry = ModelRegistry()
    registry.register_provider(FakeProvider("public"))
    registry.register_provider(FakeProvider("local"))
    registry.register_model(descriptor("cheap", "public", context_window=4096, latency=250))
    registry.register_model(
        descriptor(
            "private",
            "local",
            privacy=PrivacyLevel.LOCAL,
            context_window=16384,
            latency=50,
            input_price=0.0,
            output_price=0.0,
        )
    )
    request = ModelRequest(
        task=ModelTask.CHAT,
        payload="hello",
        required_context_window=12000,
        max_cost_usd=0.01,
        max_latency_ms=100,
        required_privacy=PrivacyLevel.PRIVATE,
    )
    selected = ModelRouter(registry).route(request)
    assert [item.model_id for item in selected] == ["private"]


def test_gateway_falls_back_only_on_transient_provider_failures() -> None:
    registry = ModelRegistry()
    first = FakeProvider("first", fail=True)
    second = FakeProvider("second")
    registry.register_provider(first)
    registry.register_provider(second)
    registry.register_model(descriptor("first-model", "first", latency=10))
    registry.register_model(descriptor("second-model", "second", latency=20))
    result = ModelGateway(registry).invoke(ModelRequest(ModelTask.CHAT, "hello"))
    assert result.provider_id == "second"
    assert result.model_id == "second-model"
    assert first.calls == 1
    assert second.calls == 1


def test_embeddings_and_reranking_are_first_class_gateway_tasks() -> None:
    registry = ModelRegistry()
    provider = FakeProvider("local")
    registry.register_provider(provider)
    registry.register_model(
        descriptor(
            "embedder",
            "local",
            privacy=PrivacyLevel.LOCAL,
            tasks=frozenset({ModelTask.EMBEDDING}),
        )
    )
    registry.register_model(
        descriptor(
            "reranker",
            "local",
            privacy=PrivacyLevel.LOCAL,
            tasks=frozenset({ModelTask.RERANK}),
        )
    )
    gateway = ModelGateway(registry)
    embedding = gateway.invoke(ModelRequest(ModelTask.EMBEDDING, "hello"))
    rerank = gateway.invoke(
        ModelRequest(
            ModelTask.RERANK,
            RerankInput("query", ("one", "two")),
        )
    )
    assert embedding.output == (0.1, 0.2, 0.3)
    assert isinstance(rerank.output, tuple)
    assert isinstance(rerank.output[0], RerankItem)


def test_same_agent_logic_can_switch_model_and_provider(tmp_path) -> None:
    public_registry = ModelRegistry()
    public_provider = FakeProvider("public")
    public_registry.register_provider(public_provider)
    public_registry.register_model(descriptor("public-model", "public"))

    private_registry = ModelRegistry()
    private_provider = FakeProvider("private")
    private_registry.register_provider(private_provider)
    private_registry.register_model(
        descriptor("private-model", "private", privacy=PrivacyLevel.PRIVATE)
    )

    platform = ReferenceAgentPlatformClient(principal=User("u"))
    sdk = AgentSDK(
        platform,
        StateStore(tmp_path / "state.db"),
        model_gateway=ModelGateway(public_registry),
    )
    request = ModelRequest(ModelTask.DECISION, "choose a safe action")
    first = sdk.model(request)
    sdk.model_gateway = ModelGateway(private_registry)
    second = sdk.model(request)
    assert first.output == "public:public-model"
    assert second.output == "private:private-model"


def test_model_gateway_propagates_immutable_sdk_trace_context(tmp_path) -> None:
    registry = ModelRegistry()
    provider = FakeProvider("p")
    registry.register_provider(provider)
    registry.register_model(descriptor("m", "p"))
    sdk = AgentSDK(
        ReferenceAgentPlatformClient(principal=User("u")),
        StateStore(tmp_path / "state.db"),
        model_gateway=ModelGateway(registry),
    )
    context = ExecutionContext(
        trace=TraceContext("00-0123456789abcdef0123456789abcdef-0123456789abcdef-01")
    )
    with sdk.context(context):
        result = sdk.model(ModelRequest(ModelTask.CHAT, "trace me"))
    assert result.traceparent == context.trace.traceparent


def test_request_constraints_cannot_loosen_application_policy() -> None:
    registry = ModelRegistry()
    registry.register_provider(FakeProvider("p"))
    registry.register_model(
        descriptor(
            "m",
            "p",
            context_window=8192,
            latency=100,
            input_price=1.0,
            output_price=1.0,
            features=frozenset({"reasoning", "structured-output"}),
        )
    )
    request = ModelRequest(
        ModelTask.DECISION,
        "x" * 100,
        estimated_input_tokens=8000,
        max_output_tokens=1024,
        max_cost_usd=100.0,
        required_capabilities=frozenset({"reasoning"}),
    )
    policy = RoutingPolicy(
        max_cost_usd=0.001,
        max_latency_ms=50,
        required_context_window=4096,
        required_privacy=PrivacyLevel.PRIVATE,
    )
    assert ModelRouter(registry).route(request, policy) == ()


def test_capability_matching_is_explicit() -> None:
    registry = ModelRegistry()
    registry.register_provider(FakeProvider("p"))
    registry.register_model(descriptor("m", "p", features=frozenset({"reasoning"})))
    gateway = ModelGateway(registry)
    request = ModelRequest(
        ModelTask.CHAT,
        "hello",
        required_capabilities=frozenset({"vision"}),
    )
    with pytest.raises(ModelRoutingError, match="no registered model"):
        gateway.invoke(request)
