"""Provider-neutral model gateway and deterministic model router (M14).

The gateway is a capability/cost/latency/context policy boundary for model
selection. It deliberately has no Agent Platform authority imports: model
outputs are untrusted data and cannot create approvals, capabilities, runs,
evidence, secrets, or policy decisions.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from enum import StrEnum
import re
import time
from typing import Protocol


_TRACEPARENT = re.compile(r"^00-[0-9a-f]{32}-[0-9a-f]{16}-[0-9a-f]{2}$")


class ModelError(RuntimeError):
    """Base model gateway error."""


class ModelContractError(ModelError, ValueError):
    """Invalid public model contract."""


class ModelRoutingError(ModelError):
    """No acceptable model/provider could satisfy a request."""


class ProviderError(ModelError):
    """Provider-side failure."""


class ProviderUnavailable(ProviderError):
    """Provider is unavailable and fallback may continue."""


class ProviderTimeout(ProviderError, TimeoutError):
    """Provider exceeded its request timeout and fallback may continue."""


class ProviderRateLimited(ProviderError):
    """Provider rejected the request because of rate limiting."""


class UnsupportedModelTask(ModelError):
    """The gateway does not implement the requested model task yet."""


class ModelTask(StrEnum):
    CHAT = "chat"
    DECISION = "decision"
    EMBEDDING = "embedding"
    RERANK = "rerank"
    VISION = "vision"
    SPEECH = "speech"


class PrivacyLevel(StrEnum):
    PUBLIC = "public"
    PRIVATE = "private"
    LOCAL = "local"

    @property
    def rank(self) -> int:
        return {PrivacyLevel.PUBLIC: 0, PrivacyLevel.PRIVATE: 1, PrivacyLevel.LOCAL: 2}[self]


@dataclass(frozen=True, slots=True)
class ModelCapabilities:
    """Capabilities advertised by a registered model.

    Declarations describe what a provider claims to support; they do not
    authorize the model to perform any Platform action.
    """

    tasks: frozenset[ModelTask]
    context_window: int
    features: frozenset[str] = frozenset()
    structured_output: bool = False
    tool_calling: bool = False
    streaming: bool = False
    vision_input: bool = False
    speech_input: bool = False

    def validate(self) -> None:
        if not self.tasks:
            raise ModelContractError("model must advertise at least one task")
        if self.context_window <= 0:
            raise ModelContractError("context_window must be positive")
        if any(not feature.strip() for feature in self.features):
            raise ModelContractError("model capability features cannot be blank")
        if ModelTask.VISION in self.tasks and not self.vision_input:
            raise ModelContractError("vision task requires vision_input")
        if ModelTask.SPEECH in self.tasks and not self.speech_input:
            raise ModelContractError("speech task requires speech_input")


@dataclass(frozen=True, slots=True)
class ModelPricing:
    """Per-token pricing in USD, expressed per one million tokens."""

    input_usd_per_million: float | None = None
    output_usd_per_million: float | None = None

    def validate(self) -> None:
        for value in (self.input_usd_per_million, self.output_usd_per_million):
            if value is not None and value < 0:
                raise ModelContractError("model pricing cannot be negative")

    def estimate(self, input_tokens: int, output_tokens: int) -> float | None:
        if self.input_usd_per_million is None or self.output_usd_per_million is None:
            return None
        return (
            input_tokens * self.input_usd_per_million
            + output_tokens * self.output_usd_per_million
        ) / 1_000_000


@dataclass(frozen=True, slots=True)
class ModelDescriptor:
    model_id: str
    provider_id: str
    capabilities: ModelCapabilities
    privacy: PrivacyLevel = PrivacyLevel.PUBLIC
    pricing: ModelPricing = field(default_factory=ModelPricing)
    estimated_latency_ms: int | None = None
    priority: int = 100
    enabled: bool = True

    def validate(self) -> None:
        if not self.model_id.strip() or not self.provider_id.strip():
            raise ModelContractError("model_id and provider_id are required")
        self.capabilities.validate()
        self.pricing.validate()
        if self.estimated_latency_ms is not None and self.estimated_latency_ms < 0:
            raise ModelContractError("estimated_latency_ms cannot be negative")


@dataclass(frozen=True, slots=True)
class RerankInput:
    query: str
    documents: tuple[str, ...]

    def validate(self) -> None:
        if not self.query.strip():
            raise ModelContractError("rerank query is required")
        if not self.documents:
            raise ModelContractError("rerank requires at least one document")
        if any(not document.strip() for document in self.documents):
            raise ModelContractError("rerank documents cannot be empty")


@dataclass(frozen=True, slots=True)
class RerankItem:
    index: int
    score: float
    document: str


@dataclass(frozen=True, slots=True)
class ModelUsage:
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0

    def validate(self) -> None:
        if min(self.input_tokens, self.output_tokens, self.total_tokens) < 0:
            raise ModelContractError("model usage cannot be negative")
        if self.total_tokens and self.total_tokens < self.input_tokens + self.output_tokens:
            raise ModelContractError("total_tokens cannot be below input + output tokens")


@dataclass(frozen=True, slots=True)
class ModelRequest:
    """Untrusted model input plus routing constraints.

    The request contains no Platform authority fields. A provider receives
    this data only to produce a model result.
    """

    task: ModelTask
    payload: object
    model_id: str | None = None
    provider_id: str | None = None
    required_context_window: int = 0
    estimated_input_tokens: int = 0
    max_output_tokens: int = 1024
    max_cost_usd: float | None = None
    max_latency_ms: int | None = None
    required_privacy: PrivacyLevel = PrivacyLevel.PUBLIC
    required_capabilities: frozenset[str] = frozenset()
    allowed_models: frozenset[str] = frozenset()
    allowed_providers: frozenset[str] = frozenset()
    allow_fallback: bool = True
    traceparent: str | None = None
    metadata: Mapping[str, str] = field(default_factory=dict)

    def validate(self) -> None:
        if self.task in (ModelTask.VISION, ModelTask.SPEECH):
            raise UnsupportedModelTask(f"{self.task.value} is reserved for a later gateway phase")
        if self.estimated_input_tokens < 0:
            raise ModelContractError("estimated_input_tokens cannot be negative")
        if self.required_context_window < 0:
            raise ModelContractError("required_context_window cannot be negative")
        if self.max_output_tokens <= 0:
            raise ModelContractError("max_output_tokens must be positive")
        if self.max_cost_usd is not None and self.max_cost_usd < 0:
            raise ModelContractError("max_cost_usd cannot be negative")
        if self.max_latency_ms is not None and self.max_latency_ms < 0:
            raise ModelContractError("max_latency_ms cannot be negative")
        if any(not capability.strip() for capability in self.required_capabilities):
            raise ModelContractError("required capability names cannot be blank")
        if self.model_id is not None and not self.model_id.strip():
            raise ModelContractError("model_id cannot be blank")
        if self.provider_id is not None and not self.provider_id.strip():
            raise ModelContractError("provider_id cannot be blank")
        if self.traceparent is not None and not _TRACEPARENT.fullmatch(self.traceparent):
            raise ModelContractError("traceparent must be a valid W3C traceparent")
        if self.task == ModelTask.RERANK:
            if not isinstance(self.payload, RerankInput):
                raise ModelContractError("rerank payload must be RerankInput")
            self.payload.validate()
        if self.task in (ModelTask.CHAT, ModelTask.DECISION) and self.payload is None:
            raise ModelContractError("model payload is required")


@dataclass(frozen=True, slots=True)
class ModelResponse:
    """Untrusted model output.

    No Platform references, authority handles, secrets or executable actions
    are exposed by this type.
    """

    task: ModelTask
    model_id: str
    provider_id: str
    output: object
    usage: ModelUsage = field(default_factory=ModelUsage)
    latency_ms: int = 0
    finish_reason: str | None = None
    estimated_cost_usd: float | None = None
    traceparent: str | None = None

    def validate(self) -> None:
        if not self.model_id or not self.provider_id:
            raise ModelContractError("model response must identify model and provider")
        self.usage.validate()
        if self.latency_ms < 0:
            raise ModelContractError("response latency cannot be negative")


@dataclass(frozen=True, slots=True)
class RouteAttempt:
    model_id: str
    provider_id: str
    outcome: str
    error_type: str | None = None
    latency_ms: int | None = None


@dataclass(frozen=True, slots=True)
class RoutingPolicy:
    """Deterministic routing policy supplied by the agent/application."""

    preferred_models: tuple[str, ...] = ()
    preferred_providers: tuple[str, ...] = ()
    max_cost_usd: float | None = None
    max_latency_ms: int | None = None
    required_context_window: int = 0
    required_privacy: PrivacyLevel = PrivacyLevel.PUBLIC
    allowed_models: frozenset[str] = frozenset()
    allowed_providers: frozenset[str] = frozenset()
    allow_fallback: bool = True

    def validate(self) -> None:
        if self.max_cost_usd is not None and self.max_cost_usd < 0:
            raise ModelContractError("max_cost_usd cannot be negative")
        if self.max_latency_ms is not None and self.max_latency_ms < 0:
            raise ModelContractError("max_latency_ms cannot be negative")
        if self.required_context_window < 0:
            raise ModelContractError("required_context_window cannot be negative")


class ModelProvider(Protocol):
    """Provider abstraction implemented by hosted, private or local adapters."""

    provider_id: str

    def complete(self, request: ModelRequest, model: ModelDescriptor) -> ModelResponse: ...

    def embed(self, request: ModelRequest, model: ModelDescriptor) -> ModelResponse: ...

    def rerank(self, request: ModelRequest, model: ModelDescriptor) -> ModelResponse: ...

    def health(self) -> bool: ...


@dataclass
class ModelRegistry:
    """Runtime registry of provider adapters and immutable model descriptors."""

    _providers: dict[str, ModelProvider] = field(default_factory=dict)
    _models: dict[str, ModelDescriptor] = field(default_factory=dict)

    def register_provider(self, provider: ModelProvider) -> None:
        provider_id = provider.provider_id.strip()
        if not provider_id:
            raise ModelContractError("provider_id is required")
        if provider_id in self._providers:
            raise ModelContractError(f"provider already registered: {provider_id}")
        self._providers[provider_id] = provider

    def register_model(self, descriptor: ModelDescriptor) -> None:
        descriptor.validate()
        if descriptor.provider_id not in self._providers:
            raise ModelContractError(
                f"provider is not registered: {descriptor.provider_id}"
            )
        if descriptor.model_id in self._models:
            raise ModelContractError(f"model already registered: {descriptor.model_id}")
        self._models[descriptor.model_id] = descriptor

    def provider(self, provider_id: str) -> ModelProvider:
        try:
            return self._providers[provider_id]
        except KeyError as exc:
            raise ModelContractError(f"unknown provider: {provider_id}") from exc

    def model(self, model_id: str) -> ModelDescriptor:
        try:
            return self._models[model_id]
        except KeyError as exc:
            raise ModelContractError(f"unknown model: {model_id}") from exc

    def models(self) -> tuple[ModelDescriptor, ...]:
        return tuple(self._models.values())

    def providers(self) -> tuple[str, ...]:
        return tuple(self._providers)


def _strictest_upper_bound(
    request_value: float | int | None,
    policy_value: float | int | None,
) -> float | int | None:
    if request_value is None:
        return policy_value
    if policy_value is None:
        return request_value
    return min(request_value, policy_value)


def _intersect_allowlists(
    request_values: frozenset[str],
    policy_values: frozenset[str],
) -> frozenset[str]:
    if request_values and policy_values:
        return request_values & policy_values
    return request_values or policy_values


@dataclass(frozen=True, slots=True)
class ModelRouter:
    """Selects candidates without invoking providers or evaluating authority."""

    registry: ModelRegistry

    def route(
        self,
        request: ModelRequest,
        policy: RoutingPolicy | None = None,
    ) -> tuple[ModelDescriptor, ...]:
        request.validate()
        effective = policy or RoutingPolicy()
        effective.validate()

        max_cost = _strictest_upper_bound(
            request.max_cost_usd,
            effective.max_cost_usd,
        )
        max_latency = _strictest_upper_bound(
            request.max_latency_ms,
            effective.max_latency_ms,
        )
        context_window = max(
            request.required_context_window,
            effective.required_context_window,
            request.estimated_input_tokens + request.max_output_tokens,
        )
        required_privacy = (
            request.required_privacy
            if request.required_privacy.rank >= effective.required_privacy.rank
            else effective.required_privacy
        )
        allowed_models = _intersect_allowlists(
            request.allowed_models,
            effective.allowed_models,
        )
        allowed_providers = _intersect_allowlists(
            request.allowed_providers,
            effective.allowed_providers,
        )

        candidates: list[ModelDescriptor] = []
        for model in self.registry.models():
            if not model.enabled or request.task not in model.capabilities.tasks:
                continue
            if request.model_id is not None and model.model_id != request.model_id:
                continue
            if request.provider_id is not None and model.provider_id != request.provider_id:
                continue
            if allowed_models and model.model_id not in allowed_models:
                continue
            if allowed_providers and model.provider_id not in allowed_providers:
                continue
            if model.privacy.rank < required_privacy.rank:
                continue
            if not request.required_capabilities.issubset(model.capabilities.features):
                continue
            if model.capabilities.context_window < context_window:
                continue
            if max_latency is not None and (
                model.estimated_latency_ms is None
                or model.estimated_latency_ms > max_latency
            ):
                continue
            estimate = model.pricing.estimate(
                request.estimated_input_tokens,
                request.max_output_tokens,
            )
            if max_cost is not None and (estimate is None or estimate > max_cost):
                continue
            candidates.append(model)

        preferred_models = {
            model_id: index for index, model_id in enumerate(effective.preferred_models)
        }
        preferred_providers = {
            provider_id: index for index, provider_id in enumerate(effective.preferred_providers)
        }

        candidates.sort(
            key=lambda item: (
                0 if item.model_id in preferred_models else 1,
                preferred_models.get(item.model_id, len(preferred_models)),
                0 if item.provider_id in preferred_providers else 1,
                preferred_providers.get(item.provider_id, len(preferred_providers)),
                item.pricing.estimate(
                    request.estimated_input_tokens,
                    request.max_output_tokens,
                )
                if item.pricing.estimate(
                    request.estimated_input_tokens,
                    request.max_output_tokens,
                ) is not None
                else float("inf"),
                item.estimated_latency_ms
                if item.estimated_latency_ms is not None
                else float("inf"),
                item.priority,
                item.provider_id,
                item.model_id,
            )
        )
        return tuple(candidates)


@dataclass(frozen=True, slots=True)
class ModelGateway:
    """Stable agent-facing model surface above the router and providers."""

    registry: ModelRegistry

    def invoke(
        self,
        request: ModelRequest,
        policy: RoutingPolicy | None = None,
    ) -> ModelResponse:
        candidates = ModelRouter(self.registry).route(request, policy)
        if not candidates:
            raise ModelRoutingError("no registered model satisfies the request and routing policy")

        effective_allow_fallback = request.allow_fallback and (
            policy.allow_fallback if policy is not None else True
        )
        attempts: list[RouteAttempt] = []
        for index, model in enumerate(candidates):
            provider = self.registry.provider(model.provider_id)
            started = time.perf_counter()
            try:
                if not provider.health():
                    raise ProviderUnavailable(
                        f"provider is unhealthy: {provider.provider_id}"
                    )
                if request.task in (ModelTask.CHAT, ModelTask.DECISION):
                    response = provider.complete(request, model)
                elif request.task == ModelTask.EMBEDDING:
                    response = provider.embed(request, model)
                elif request.task == ModelTask.RERANK:
                    response = provider.rerank(request, model)
                else:
                    raise UnsupportedModelTask(request.task.value)
                response.validate()
                if (
                    response.model_id != model.model_id
                    or response.provider_id != model.provider_id
                ):
                    raise ModelContractError("provider returned a mismatched model/provider identity")
                if response.task != request.task:
                    raise ModelContractError("provider returned a mismatched model task")
                elapsed_ms = int((time.perf_counter() - started) * 1000)
                normalized = ModelResponse(
                    task=response.task,
                    model_id=response.model_id,
                    provider_id=response.provider_id,
                    output=response.output,
                    usage=response.usage,
                    latency_ms=max(response.latency_ms, elapsed_ms),
                    finish_reason=response.finish_reason,
                    estimated_cost_usd=model.pricing.estimate(
                        response.usage.input_tokens,
                        response.usage.output_tokens,
                    ),
                    traceparent=request.traceparent,
                )
                normalized.validate()
                attempts.append(
                    RouteAttempt(
                        model.model_id,
                        model.provider_id,
                        "success",
                        latency_ms=normalized.latency_ms,
                    )
                )
                return normalized
            except (ProviderUnavailable, ProviderTimeout, ProviderRateLimited) as exc:
                elapsed_ms = int((time.perf_counter() - started) * 1000)
                attempts.append(
                    RouteAttempt(
                        model.model_id,
                        model.provider_id,
                        "fallback",
                        type(exc).__name__,
                        elapsed_ms,
                    )
                )
                if not effective_allow_fallback or index == len(candidates) - 1:
                    raise ModelRoutingError(
                        f"all model candidates failed; attempts={attempts}"
                    ) from exc
            except ModelError:
                raise
            except Exception as exc:
                raise ModelRoutingError(
                    f"provider contract failed for {model.provider_id}/{model.model_id}"
                ) from exc
        raise ModelRoutingError(f"no model response; attempts={attempts}")
