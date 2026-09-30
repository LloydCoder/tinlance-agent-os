# Tinlance Agentic OS Architecture

## Boundary

Tinlance Agentic OS is the human/agent/organization environment above Tinlance Agent
Platform. It owns workspaces, sessions, tasks, workflows, applications, presentation,
and system integration. Tinlance Agent Platform owns authority and governed execution.

## Dependency direction

`contracts -> domain -> services -> integrations -> apps`

The Agent Platform integration is an adapter boundary. OS code must not import Agent
Platform implementation internals.

## Authority boundary

`User intent -> OS task -> Platform request -> Platform authorization/policy/approval
-> Platform execution -> Platform evidence/events -> OS presentation`

Agent OS may compose and request work. It may not independently authorize consequential
actions.

## Agent Platform API v1.1

The OS adapter uses a provider-neutral transport and the Platform v1.1 request/response envelope.

Supported operations:

- principal.get
- agents.list
- runs.create
- runs.cancel
- capabilities.list
- approvals.request
- runs.events
- runs.evidence
- health

Request identity is propagated with tenant/subject context, a fresh X-Request-ID, optional W3C traceparent, and a bearer credential. Non-idempotent run creation, cancellation and approval requests are never automatically retried.

The Platform is authoritative for identity, tenant membership, authorization, policy and approval. Agent OS treats returned approval and evidence identifiers as opaque references.

## Core M0 objects

- User
- Workspace
- Session
- Agent
- Task
- Run reference
- Capability reference
- Approval reference
- Evidence reference
- Event

An OS Session is not a Platform Run. A session may contain multiple tasks and a task may
produce multiple Platform runs.

## Planes

### Experience plane
CLI, future desktop, workspace and human interaction.

### OS control plane
Agent lifecycle, sessions, tasks, workflows and context.

### Platform authority plane
Identity, tenancy, authorization, policy, approvals, budgets and governed execution.
This remains in Agent Platform.

### Evidence/telemetry plane
Platform evidence/events plus OS correlation and presentation. The OS does not replace
Platform evidence authority.

## Future integration model

```
Agentic OS
   |
   +-- Agent Platform adapter
   +-- FDSE adapter
   +-- FAS adapter
   +-- TADS adapter
   +-- domain/product adapters
   |
   +-- System abstractions
```

Domain products remain optional integrations and never become Agent OS core dependencies.

## Current implementation boundary

M0–M11 repository capabilities are implemented and tested. The following are intentionally deployment/provider seams rather than missing repository features: enterprise IdP/SSO, hosted fleet control, production telemetry backend, artifact signing service, desktop toolkit, durable Platform infrastructure and production sandbox supervision.

The historical M0 non-goals below are retained only as historical scope notes; they do not override the current roadmap or implementation.

## M0 historical non-goals

- desktop shell
- workflow engine implementation
- memory/vector database
- extension runtime
- Linux process sandbox
- direct model-provider integration
- replacement authorization engine
- replacement evidence/audit store


## M12 Agent Lifecycle Runtime

The lifecycle kernel is an OS control-plane responsibility. It does not create authority.

### Agent definition

`AgentDefinition` binds:

- stable agent ID;
- workspace;
- name and immutable registered version;
- entrypoint identity;
- declared capability references;
- runtime configuration;
- restart policy.

The declaration is descriptive. Capability authority is still evaluated by Agent Platform.

### State machine

The runtime enforces an explicit transition graph:

```text
REGISTERED -> VALIDATING -> READY -> STARTING -> RUNNING
RUNNING -> PAUSING -> PAUSED -> RESUMING -> RUNNING
RUNNING -> STOPPING -> STOPPED
RUNNING/STARTING/PAUSING/RESUMING/STOPPING -> CRASHED
CRASHED -> RECOVERING -> STARTING
CRASHED -> FAILED
```

Every transition is persisted with an optimistic state-version check in the same SQLite transaction as its lifecycle event.

### Health and recovery

A running agent owns a durable heartbeat lease. The runtime refreshes the lease at the configured interval. A new process can call `recover_orphans` to identify expired running leases and transition those agents to `CRASHED` before applying restart policy.

Restart counts are durable. Exceeding the configured restart budget transitions the agent to `FAILED` rather than creating an unbounded restart loop.

### Event determinism

Lifecycle events use a deterministic SHA-256 identifier derived from agent ID, per-agent sequence and event type. Sequence numbers are allocated transactionally, so lifecycle state and its event cannot commit independently.

### Version binding

An agent ID cannot be re-registered against a different version. This prevents a runtime restart from silently replacing the implementation associated with an existing durable identity.


## M13 Agent Developer Surface

The M13 SDK is the official application/developer layer between agent code and the OS/Platform contracts.

    Developer code
        |
        v
    Agent SDK / Application SDK
        |
        +--> AgentManifest / CapabilityDeclaration
        +--> M12 AgentRuntime
        +--> Session / Task helpers
        +--> Workflow helpers
        +--> ExecutionResult / EvidenceRef
        +--> ApprovalWorkflow
        +--> Idempotency / TraceContext
        |
        v
    Agent Platform client
        |
        v
    Platform authority

### SDK responsibilities

The SDK owns developer ergonomics and contract composition:

- scaffold validated agent applications;
- bind an application to an M12 runtime;
- create and type session/task/workflow handles;
- carry immutable execution context;
- generate deterministic idempotency keys;
- durably claim and complete SDK consequential operations;
- request Platform approvals;
- normalize execution results, events and evidence references;
- translate boundary failures into structured SDK errors.

### SDK non-responsibilities

The SDK MUST NOT:

- decide whether a capability is authorized;
- mint capability grants;
- validate an approval as sufficient authority;
- issue or handle raw secrets as authority;
- execute tools outside Platform governance;
- write authoritative evidence;
- bypass Platform policy;
- treat a manifest declaration as an actual permission.

### Idempotency protocol

For consequential SDK operations:

1. validate the caller-supplied or deterministic idempotency key;
2. atomically claim the operation in the durable OS idempotency ledger;
3. send the same key to the Platform client;
4. record the resulting Platform reference;
5. on replay, return the recorded reference;
6. after a crash between claim and Platform completion, retry the same logical operation using the same key.

The Platform remains responsible for server-side idempotency and exactly-once consequential side effects.

### Trace propagation

ExecutionContext is immutable. TraceContext validates W3C traceparent. When the concrete Platform adapter supports trace binding, the SDK creates a derived adapter carrying the same trace context rather than mutating shared client state. This follows OpenTelemetry's immutable context and propagation model.

## M14 Model Gateway + Router

The model path is deliberately separate from the authority path:

```text
Agent code
   |
   v
Agent SDK
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

The gateway owns provider abstraction, model registration, capability matching, routing policy, fallback and normalized model results. It does not own identity, authorization, approvals, budgets, secrets, tool execution or evidence authority.

### Routing contract

A `ModelRequest` describes the model task and routing constraints. A `RoutingPolicy` supplies application-level constraints. The router applies the stricter constraint whenever both exist. This prevents an agent request from widening an application's model, provider, privacy, cost, latency or context boundary.

Candidate admission requires:

- task capability;
- requested model/provider allowlists;
- application allowlists;
- required capability features;
- sufficient context window for estimated input plus maximum output;
- required privacy level;
- declared latency within the ceiling;
- declared pricing within the cost ceiling when a ceiling is enforced.

Candidates are then ordered deterministically by preferred model/provider, estimated cost, estimated latency, priority and stable identifiers.

### Fallback

Fallback is restricted to transient provider failures: unavailable, timeout and rate-limit conditions. Invalid requests, contract violations and malformed provider responses fail closed. The gateway never retries a failed model with a different model merely because a model response is semantically undesirable; quality evaluation belongs to later evaluation/orchestration layers.

### Model output boundary

`ModelResponse.output` is untrusted data. No model output is converted into a Platform capability, approval, run, evidence reference, secret or policy decision. M14 intentionally contains no imports from the Platform authority contracts.

### Current tasks

M14 implements chat, decision, embedding and reranking. Vision and speech are explicit future task types and are rejected until their contracts, provider semantics, privacy handling and tests are defined.


## M15 Context + Trusted Memory

M15 makes context and persistent memory an explicit OS control-plane subsystem rather than an untyped text store.

Memory flow:

Agent / SDK -> MemoryStore -> workspace and scope checks -> classification ceiling -> provenance/version validation -> poisoning detector -> retrieval -> trust-separated context assembly.

### Memory scope model

| Scope | Scope identity | Intended lifetime |
|---|---|---|
| Working | active session | short-lived working state |
| Session | session ID | one interaction session |
| Task | task ID | one task lifecycle |
| Agent | agent ID | agent-specific persistent knowledge |
| Long-term | workspace ID | workspace-scoped durable knowledge |

All records additionally carry the workspace and agent identity. Session/task scopes cannot be retrieved from another active session/task, even when the caller knows the memory ID.

### Provenance and versioning

Every write records source type, source ID, optional actor/origin, collection time and a parent digest when updating an existing memory key. The content digest covers identity, version, content and provenance. Updates require an explicit expected version and REPLACE conflict policy; stale writers fail rather than silently overwrite newer memory.

### Trust and classification

Classification controls confidentiality; trust controls how retrieved content may be interpreted. They are intentionally separate. TRUSTED_INSTRUCTION is reserved for system/platform/user-sourced instruction records; external and agent-originated content defaults to untrusted. Classification ceilings prevent a caller from retrieving content above its declared clearance.

Trust metadata is never an authorization grant. Memory cannot authorize a Platform run or capability.

### Poisoning and quarantine

M15 performs deterministic screening of candidate writes for common persistent-prompt-injection, exfiltration, security-bypass and credential/key patterns. A match changes the record to QUARANTINED and MemoryTrust.QUARANTINED. Quarantined records are excluded from normal retrieval and are exposed only through an explicit quarantine-inclusive path.

The detector is deliberately conservative and deterministic; it is a security signal, not a semantic truth oracle. Later classifiers can augment it without changing the storage contract.

### Context assembly

The assembler preserves trust distinctions instead of concatenating all retrieved text. Downstream model prompting must explicitly choose how to render each channel. No retrieved memory is automatically converted into an instruction, Platform authorization, approval, secret or evidence reference.
