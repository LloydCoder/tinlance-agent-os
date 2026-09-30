# M14 Model Gateway + Router — Completion Record

**Status: IMPLEMENTATION COMPLETE — pending CI/merge verification**

M14 adds the official model developer surface between Agent SDK code and model providers:

```text
Agent
  |
  v
Model Gateway
  |
  v
Model Router
  |
  +--> hosted provider
  +--> private provider
  +--> local provider
```

## Implemented

- provider-neutral `ModelProvider` protocol;
- runtime `ModelRegistry` for provider adapters and immutable model descriptors;
- task-aware model capabilities;
- explicit capability-feature matching;
- deterministic routing;
- preferred model/provider ordering;
- model/provider allowlists;
- strict cost ceilings;
- strict latency ceilings;
- context-window admission using required context plus estimated input and maximum output;
- privacy-level routing for public/private/local deployments;
- transient provider fallback for unavailable, timeout and rate-limit failures;
- decision-model task support;
- embeddings;
- reranking;
- model usage and cost normalization;
- W3C traceparent propagation from the M13 SDK context;
- local/private model support through provider descriptors and adapters;
- stable `AgentSDK.model()` entry point;
- reference tests proving model/provider switching without agent-logic changes;
- architecture tests proving the model gateway has no Platform-authority imports.

Vision and speech are explicit future task types and are rejected by M14 rather than being partially implemented.

## Routing safety

Application policy is the upper authority for model routing. A request cannot loosen:

- maximum cost;
- maximum latency;
- minimum privacy;
- allowed model set;
- allowed provider set;
- context-window requirements.

Where both request and policy constraints exist, the router applies the stricter constraint. Unknown pricing or latency data fails closed when the corresponding ceiling is enforced.

## Authority boundary

M14 does **not**:

- authorize an agent;
- grant capabilities;
- create or validate approvals;
- create Platform runs;
- execute tools;
- issue or handle Platform secrets as authority;
- create authoritative evidence;
- interpret model output as authorization.

`ModelResponse.output` is untrusted application data. The gateway has no dependency on the Agent Platform authority contracts.

## Failure model

Automatic fallback is restricted to transient provider failures. Contract violations, invalid model responses and non-transient gateway errors fail closed instead of silently switching semantics.

Every returned response identifies the selected provider/model and includes normalized usage, latency and estimated cost. Prompt/response payloads are not written to OS telemetry by the gateway.

## Acceptance

The reference-agent path is:

```text
AgentSDK.model(request)
        |
        v
ModelGateway
        |
        v
ModelRouter
        |
        +--> Provider A / Model A
        |
        +--> Provider B / Model B
```

Changing the registered provider/model configuration does not require changes to the agent's model invocation logic.

## Research alignment

M14 follows current guidance emphasizing:

- centralized model abstraction and provider switching;
- task-appropriate model selection;
- explicit cost/consumption ceilings;
- resilience and controlled fallback;
- immutable distributed tracing context;
- separation of agent identity/authorization from model behavior.

References:

- NIST AI Agent Standards Initiative: https://www.nist.gov/artificial-intelligence/ai-agent-standards-initiative
- NIST software/AI agent identity and authorization concept paper:
  https://csrc.nist.gov/pubs/other/2026/02/05/accelerating-the-adoption-of-software-and-ai-agent/ipd
- OWASP Top 10 for Agentic Applications 2026:
  https://genai.owasp.org/resource/owasp-top-10-for-agentic-applications-for-2026/
- OpenTelemetry Context:
  https://opentelemetry.io/docs/specs/otel/context/
- AWS Agentic AI Lens model-selection guidance:
  https://docs.aws.amazon.com/wellarchitected/latest/agentic-ai-lens/agentperf02-bp02.html
- AWS generative-AI gateway guidance:
  https://docs.aws.amazon.com/prescriptive-guidance/latest/gen-ai-lifecycle-operational-excellence/preprod-architecting.html
