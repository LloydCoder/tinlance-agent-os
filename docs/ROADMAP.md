# Tinlance Agentic OS Roadmap

## Completion definition

A milestone is **complete** when the repository-owned contracts, implementation, tests, architecture constraints and documentation for that milestone exist and CI verifies them. A milestone is **not** claimed to include external infrastructure that belongs to a deployment/provider.

| Milestone | Scope | Status |
|---|---|---|
| M0 | Architecture Foundation | COMPLETE |
| M1 | Agent Platform Adapter | COMPLETE |
| M2 | Local Agent OS Daemon | COMPLETE |
| M3 | Workspace + Sessions + Tasks | COMPLETE |
| M4 | Workflow Engine | COMPLETE |
| M5 | Context + Memory | COMPLETE |
| M6 | Agent Application Model | COMPLETE |
| M7 | System Integration | COMPLETE |
| M8 | Desktop/Shell foundation | COMPLETE |
| M9 | Extensions | COMPLETE |
| M10 | Enterprise / Remote OS foundation | COMPLETE |
| M11 | Production / Distribution foundation | COMPLETE |
| M12 | Agent Lifecycle Runtime | COMPLETE |
| M13 | Agent SDK / Application SDK | COMPLETE |
| M14 | Model Gateway + Model Router | COMPLETE |
| M15 | Context + Trusted Memory | COMPLETE |
| M16 | Real Workflow Runtime | COMPLETE |
| M17 | Multi-Agent Runtime | COMPLETE |
| M18 | Agent Ecosystem Runtime | COMPLETE |
| M19 | Agent Workspace & Channels | COMPLETE |
| M20 | Local/Remote Agent Runtime | COMPLETE |
| M21 | Agent OS Observability | COMPLETE |
| M22 | Reference Agents | COMPLETE |
| M23 | Agent OS Conformance & Red Team Suite | COMPLETE |
| M24 | Production Agent OS | COMPLETE |
| M25 | Enterprise Forensic Hardening | COMPLETE |
| M26 | Agent Directory & Desired-State Management | COMPLETE |
| M27 | Enterprise Workspace & Organization Fabric | COMPLETE |
| M28 | Event, Signal & Reactive Runtime | COMPLETE |
| M29 | Scheduler & Job Runtime | COMPLETE |
| M30 | Context & Knowledge Fabric | COMPLETE |
| M31 | Connectors & Data Spaces | COMPLETE |\n| M32 | Resource, Cost & Capacity Runtime | COMPLETE |\n| M33 | Evaluation & Agent Quality Runtime | COMPLETE |

## M0 — Architecture Foundation

Stable OS domain contracts, authority boundary, Session-vs-Run ADR, domain-product independence, threat model, architecture tests and CI.

## M1 — Agent Platform Adapter

Provider-neutral client contract, versioned transport, authenticated request context, strict response validation, bounded idempotent retries, lifecycle/capability/approval/event/evidence mappings.

## M2 — Local Daemon

Unix-domain socket control plane with same-user peer validation where supported, restrictive socket permissions, bounded line protocol, request limits, timeout and controlled shutdown.

## M3 — Durable State

SQLite workspace/session/task/event/memory/workflow persistence with foreign keys, WAL, synchronous durability and indexes.

## M4 — Workflow

Validated DAG definitions, deterministic ready-step calculation and explicit execution lifecycle transitions.

## M5 — Context + Memory

Workspace/scope isolation, classification and fail-closed handling for confidential/restricted local memory.

## M6 — Applications

Declarative manifests, capability requests and lifecycle state transitions.

## M7 — System Integration

Root-confined filesystem operations, constrained process execution and notification abstraction.

## M8 — Shell

Toolkit-neutral presentation/shell command model. A full desktop environment remains an integration project.

## M9 — Extensions

Capability-scoped extension lifecycle without duplicating Platform authorization.

## M10 — Enterprise

Remote-agent registry and secure endpoint validation as a seam for a future fleet/control plane.

## M11 — Distribution

Content-addressed artifact verification and staged/apply/rollback state management. Production signing and provenance are deployment/provider concerns.

## Cross-cutting gates

Every milestone must preserve:

1. Platform as the sole authority for consequential execution.
2. No imports from Platform implementation internals.
3. No core dependency on FAS, FDSE, TADS, ThreatFade or Hezqara.
4. Typed boundary contracts.
5. Unit + contract + architecture coverage.
6. Python 3.12–3.14 compatibility.
7. Ruff, format, mypy, coverage and dependency audit.
8. No mutable third-party GitHub Action references in CI.

## Integration contract

The authoritative Agent Platform adapter contract is [docs/architecture/agent-platform-integration.md](architecture/agent-platform-integration.md). Changes to the wire contract must update the adapter, contract tests, Platform-side conformance tests and documentation together.

## Next evolution

Future work should deepen provider integrations and production hardening rather than silently expanding the OS into a duplicate Platform authority plane.


## M12 — Agent Lifecycle Runtime

M12 adds the first real agent lifecycle kernel above the M0-M11 OS foundation.

### Scope

- typed `AgentDefinition`, runtime configuration and restart policy;
- durable agent registration and immutable version binding;
- explicit lifecycle state machine;
- start, run, pause, resume, stop and recovery operations;
- durable health/heartbeat leases;
- crash detection after process restart;
- bounded restart policy with restart counters and fail-closed exhaustion;
- optimistic-concurrency protected lifecycle transitions;
- deterministic, append-only lifecycle events.

### Lifecycle

```text
REGISTERED
    -> VALIDATING -> READY
    -> STARTING -> RUNNING
    -> PAUSING -> PAUSED
    -> RESUMING -> RUNNING
    -> STOPPING -> STOPPED
    -> RECOVERING -> STARTING
    -> CRASHED -> RECOVERING | FAILED
```

Agent OS owns lifecycle state and runtime intent. Agent Platform remains authoritative for identity, capabilities, authorization, policy, approvals, budgets, execution, secrets, sandboxing and evidence.

### Acceptance

An agent can durably execute:

```text
register -> validate -> start -> run -> pause -> resume -> stop
                                  |
                                  +-> crash -> recover
```

Lifecycle events have deterministic IDs and monotonically increasing per-agent sequence numbers. Heartbeat leases allow a subsequent process to identify abandoned running agents and reconcile them to `CRASHED` before recovery.

### Cross-cutting gates

M12 preserves all existing M0-M11 gates and adds:

- version binding cannot silently substitute an agent implementation;
- state transitions use an expected-state/version check;
- lifecycle event and state changes commit atomically;
- heartbeat leases are durable;
- restart exhaustion fails closed;
- lifecycle telemetry contains no model/tool/secret authority;


## M13 — Agent SDK / Application SDK

M13 is the official high-level developer surface above the existing Agent Platform client and M12 lifecycle runtime.

### Scope

- agent scaffolding and validated application manifests;
- lifecycle/runtime construction without low-level Platform HTTP;
- session and task helpers;
- typed workflow helpers;
- declarative capability requirements;
- Platform-backed approval requests;
- typed execution results, events and opaque evidence references;
- structured SDK errors;
- durable idempotency claims and replay-safe consequential operations;
- immutable execution context with W3C trace-context validation and adapter propagation;
- contract validation at the public SDK boundary.

### Authority rule

The SDK is a composition layer. It does not implement authorization, capability grants, policy evaluation, approval validity, secrets, sandboxing, budgets or authoritative evidence. Capability declarations are requests; approval objects and evidence references are opaque Platform outputs.

### Golden path

```text
AgentSDK.scaffold()
    -> AgentApplication
    -> M12 AgentRuntime
    -> SDK.session()
    -> SDK.task()
    -> SDK.execute()
    -> Platform create_run
    -> SDK.result()
```

A developer can build a reference agent entirely through the SDK surface without constructing Platform HTTP envelopes.

### Reliability

SDK consequential operations use explicit or deterministic idempotency keys. A durable SQLite idempotency ledger claims an operation before the Platform call and records its result afterward. The Platform request carries the same key, allowing recovery after an OS process failure. Exactly-once side effects remain a Platform responsibility.

### Tracing

SDK execution contexts are immutable and validate W3C traceparent values. When the concrete Platform adapter supports trace binding, the SDK propagates the trace context into the Platform request. This follows OpenTelemetry's context-propagation model. citeturn1search0turn1search1

### Acceptance

The M13 reference test proves:

- scaffold → validate manifest/capabilities;
- construct and register an M12 runtime;
- create a workspace/session/task;
- execute through the high-level SDK;
- retrieve typed execution/evidence results;
- request an opaque approval;
- replay execution/approval safely with the same idempotency key;
- preserve execution context and trace metadata;
- compose and complete a typed workflow;
- reject invalid public contracts.

## M14 — Model Gateway + Model Router

M14 is the provider-neutral model control surface above hosted, private and local model providers.

### Scope

- provider abstraction and runtime registry;
- model descriptors and capability matching;
- deterministic routing with preferred models/providers;
- strict cost, latency, privacy and context-window policy;
- model/provider allowlists;
- transient failure fallback;
- decision models, embeddings and reranking;
- SDK integration through `AgentSDK.model()`;
- trace-context propagation;
- authority-boundary architecture tests.

Vision and speech are reserved for a later milestone and are rejected explicitly by M14 rather than exposed as partially implemented capabilities.

### Authority rule

The Model Gateway is a model-selection and provider-integration layer, not an authorization layer. Model output is untrusted data. M14 cannot grant capabilities, approve actions, create Platform runs, execute tools, issue Platform authority, or create authoritative evidence.

### Policy rule

A request cannot weaken an application routing policy. When both specify constraints, the stricter cost, latency, privacy, context, model-allowlist and provider-allowlist constraint applies. Cost- or latency-constrained routing fails closed when the registry lacks the corresponding estimate.

### Acceptance

A reference agent calls `AgentSDK.model(ModelRequest(...))` without knowing provider-specific APIs. Replacing the registered model/provider changes routing configuration, not agent logic.


## M15 — Context + Trusted Memory

M15 replaces the historical M5 memory primitive with a real agent memory subsystem. Persistent memory is treated as a security-relevant state surface because retrieved state can influence future reasoning and tool use across sessions. OWASP identifies this as ASI06 Memory & Context Poisoning. See the OWASP Agentic Applications 2026 source cited in the M15 security documentation.

### Components

- working memory;
- session memory;
- task memory;
- agent memory;
- workspace long-term memory;
- immutable provenance records and parent-digest chains;
- public/internal/confidential/restricted classification;
- trusted-instruction, verified-fact, untrusted-content and quarantined trust classes;
- retention defaults plus explicit TTL/expiry;
- tombstone deletion;
- immutable versions with compare-and-swap conflict detection;
- deterministic retrieval;
- poisoning detection and quarantine;
- trust-separated context assembly.

### Scope boundary

Every memory record is bound to exactly one workspace and agent. Session and working memory are bound to a session; task memory is bound to a task; agent memory is bound to the agent; long-term memory is bound to the workspace. Retrieval applies the same boundary before content is exposed.

### Confidentiality boundary

Classification is monotonic. A retrieval request has a maximum classification ceiling; records above that ceiling are omitted. The OS never downgrades a record merely to make it fit a lower clearance. Restricted/confidential content therefore fails closed rather than leaking through context assembly.

### Trust boundary

Trust is metadata, not authority. User/system/platform instructions may be represented as trusted instructions, verified facts are separated from instructions, and external/agent-generated content remains untrusted by default. Suspicious content is stored only in the quarantined state and is excluded from normal retrieval.

Memory trust never creates Platform capability, approval, execution authority, secret access or evidence authority.

### Poisoning controls

M15 performs deterministic pre-persistence screening for common instruction-hijack, exfiltration, security-bypass and credential/key patterns. Detection is a quarantine signal rather than a claim of semantic truth. Quarantined entries remain inspectable only through an explicit quarantine-inclusive retrieval path.

### Context assembly

MemoryStore.assemble_context() produces four separate channels: trusted instructions, verified facts, untrusted content and quarantined content. Future vector/embedding retrieval can plug into the same contract without changing the trust boundary.

### Acceptance

A reference agent can write memory, close its process, reopen the SQLite store, and retrieve the memory in a later session while retaining provenance and version metadata. Cross-workspace, cross-agent, cross-session and over-classification reads fail closed; suspicious memory is quarantined; explicit deletion and expiry remove records from active retrieval.


## M16 — Real Workflow Runtime

M16 upgrades the deterministic workflow DAG into a durable, recovery-oriented runtime.

### Runtime semantics

- sequential dependency execution;
- parallel execution of independently ready branches;
- deterministic conditions;
- bounded retries with exponential backoff;
- workflow and step deadline/timeout propagation;
- cancellation and Platform-run cancellation propagation;
- durable approval gates;
- durable human-input gates;
- compensation after failed consequential work;
- per-step checkpoints and append-only workflow events;
- crash recovery and resume;
- event-triggered workflow instances;
- persisted schedules and due-schedule firing;
- stable per-instance/per-step idempotency keys;
- explicit Platform Run mapping through the Agent Platform adapter.

### Durability invariant

A consequential step has one stable idempotency key for its entire lifetime. A process crash can therefore leave the step in RUNNING; recovery moves the durable state back to PENDING without generating a new key. The next Platform call reuses the same key. The OS does not claim exactly-once side effects; the Platform remains authoritative for execution idempotency.

### Acceptance

The M16 suite verifies sequential and parallel branches, conditions, retry behavior, approval/input pauses, cancellation, compensation, scheduling/event triggers, crash recovery, idempotency continuity and Platform-run mapping across Python 3.12–3.14.

SQLite remains a local durable store. WAL improves reader/writer concurrency but still permits only one writer at a time, so the runtime uses short explicit transactions and optimistic workflow-instance versions rather than treating SQLite as a distributed workflow coordinator.


## M17 — Multi-Agent Runtime

M17 adds coordination primitives for supervisor/child-agent execution without creating a second authority plane.

- authenticated agent principals with tenant/workspace binding;
- durable parent/child task ownership;
- delegation with explicit capability-subset verification;
- signed, digest-bound agent messages;
- monotonic per-task message sequencing;
- trace continuity across delegation hops;
- result aggregation limited to supervisor-owned children;
- cancellation propagation through a task tree.

Identity authentication and capability verification are adapter contracts; authoritative identity, capability grants and consequential execution remain Platform-owned.


## M18 — Agent Ecosystem Runtime

M18 unifies skills, applications, extensions, connectors and agent packages behind a verified package boundary. Installation verifies the artifact digest and signature, dependency resolution is version-exact, quarantine blocks activation, rollback uses a previously verified artifact, and capability grants require an explicit Platform authorization result. Manifest claims never mint capabilities.

## M19 — Agent Workspace & Channels

M19 makes workspace presentation channel-neutral. Web, CLI, Desktop, API, Messaging and Notifications are represented by one durable channel contract rather than separate lifecycle systems.

### Workspace surface

A workspace exposes agents, applications, skills, sessions, tasks, workflows, memory, integrations, events and channels.

### Channel invariants

A channel is bound to exactly one workspace. A bound channel may carry session, task and agent identity plus a stable trace identity. Cross-workspace bindings and forged agent/session/task combinations fail closed. Channel handoff preserves lifecycle identity and trace continuity; it does not create Platform authority.

### Acceptance

The same agent/session/task can move between Web, CLI, Desktop, API, Messaging and Notification channels without changing lifecycle identifiers or trace continuity. Channel envelopes are durable and remain presentation-plane data.

## M20 — Local/Remote Agent Runtime

M20 strengthens local process supervision and remote-agent execution without creating a second authority plane.

### Local runtime

- bounded process supervision with CPU, address-space and process-count limits where the host exposes POSIX resource controls;
- root-bound filesystem capability bindings;
- explicit network endpoint policy;
- deterministic process lifecycle supervision.

### Remote runtime

- workspace/tenant-bound endpoint enrollment;
- authenticated endpoint identity and fingerprint verification;
- durable endpoint state;
- heartbeats, stale-endpoint detection and reconnect;
- draining and disconnect lifecycle;
- deterministic workspace fleet routing;
- durable remote task assignments;
- stable remote idempotency keys;
- remote cancellation;
- Platform Run mapping for consequential execution.

### MCP boundary

M20 uses an MCP transport adapter rather than inventing a second remote tool wire protocol. The adapter targets the current MCP ecosystem and keeps long-lived Agent OS lifecycle state outside transport sessions. MCP's current direction is stateless at the protocol core, with explicit handles/extensions for stateful or long-running work; the OS retains ownership of its durable task/endpoint lifecycle. citeturn1search10turn1search12

### Acceptance

A remote agent can:

    enroll
      -> authenticate
      -> healthy
      -> assigned work
      -> execute through Platform
      -> report/transport result
      -> drain
      -> disconnect

without becoming a second authority plane. Platform identity, authorization, capability grants, approvals, policy, consequential execution and evidence remain authoritative in Agent Platform.


## M21 — Agent OS Observability

M21 uses OpenTelemetry Python tracing and metrics with OTLP export configuration. Trace context can cross SDK/model/Platform boundaries using W3C propagation. GenAI model telemetry uses current GenAI semantic attribute names and does not record prompt/completion content by default. Operational measurements cover agent uptime, task/workflow/model/approval latency, token usage, model cost, tool calls, retries, failures, memory operations, queue depth and recovery.

## M22 — Reference Agents

M22 defines four canonical Tinlance reference agents: Research, Cybersecurity, FDE/Engineering and World Intelligence. Each uses the same governed Agent SDK execution path, Context/Memory, Model Gateway, Skill surface, Platform-backed execution, approvals, evidence/results, trace context and structured SDK error boundary. Reference agents do not implement a second authorization or execution plane.


## M23 — Agent OS Conformance & Red Team Suite

M23 is the adversarial acceptance layer. It actively attempts identity spoofing, confused-deputy delegation, tenant escape, capability forgery, approval replay/idempotency abuse, workflow state manipulation, memory/context poisoning, skill and extension escalation, inter-agent impersonation, remote endpoint replay, recovery races, supply-chain tampering, distribution downgrade abuse, and observability leakage. A passing case means the attempted invariant violation is rejected or safely contained.

## M24 — Production Agent OS

Production distribution is enforced through signed release artifacts, SBOM generation, SLSA/in-toto provenance attestations, staged release channels, health-gated rollout, automatic rollback, downgrade prevention, migration/backup boundaries, disaster-recovery procedures, security response, and release evidence. The production release workflow uses GitHub artifact attestations and Sigstore/Cosign rather than inventing a private signing protocol.


## M25 — Enterprise Forensic Hardening

M25 is the post-M24 forensic hardening pass. It addresses concrete residual gaps found by adversarial review rather than introducing another authority plane.

### Scope

- release manifest minimum-version validation and enforcement;
- strict signature/SBOM/provenance evidence shape validation;
- safe cancellation of staged releases when backup preparation fails;
- rollback only after the new version is actually active;
- trusted/verified memory promotion restricted to system/platform/user provenance;
- supervised-process environment allowlisting against loader/interpreter injection;
- correct validation of Unix-domain fleet endpoints;
- immutable SHA-pinned GitHub Actions enforced by CI.

### Acceptance

- production release tests cover invalid evidence, minimum-version rejection, backup failure and pre-activation migration failure;
- memory conformance rejects agent/external self-promotion to verified facts;
- remote runtime tests reject dangerous process environment variables;
- fleet tests accept absolute Unix socket endpoints;
- CI fails if any workflow action is referenced by a mutable tag or branch.

M25 does not claim that external signing services, telemetry collectors, enterprise identity, fleet control planes, operating-system sandboxing or disaster-recovery environments are implemented inside this repository.

## M26 — Agent Directory & Desired-State Management

M26 extends the existing M12 lifecycle registry into an explicit desired-state control surface. The directory records what an Agent OS workspace intends to run, while M12 remains the observed lifecycle runtime.

### Scope

- durable desired agent definitions;
- generation-based compare-and-swap updates;
- version, capability, configuration and rollout-channel metadata;
- explicit OS/Platform compatibility metadata;
- desired states for running, paused and stopped agents;
- deterministic desired-vs-observed reconciliation plans;
- blocked plans for missing or cross-workspace observations;
- read-only reconciliation planning so planning cannot create execution authority.

### Acceptance

A desired agent definition is durably persisted, can be updated only with the expected generation, and produces a deterministic reconciliation plan against M12 observed state. Version/configuration/capability drift is surfaced explicitly. No directory record grants a Platform capability or executes an agent.

## M27 — Enterprise Workspace & Organization Fabric

M27 introduces an OS-owned organizational and workspace composition layer.

### Scope

- organization, project and environment hierarchy;
- development/staging/production environment semantics;
- workspace-to-hierarchy binding;
- layered configuration inheritance;
- workspace templates;
- active/archived lifecycle;
- generation-protected workspace updates;
- deterministic workspace export;
- cross-hierarchy integrity checks.

### Boundary

M27 describes OS context and desired configuration. It does not authorize users/agents, grant capabilities, enforce Platform policy, or create execution authority.

### Acceptance

An existing OS workspace can be bound to exactly one organization/project/environment hierarchy, effective configuration resolves deterministically from parent to workspace scope, stale writers are rejected by generation checks, lifecycle changes are durable, and invalid cross-hierarchy bindings fail closed.

## M28 — Event, Signal & Reactive Runtime

- durable workspace-scoped events;
- typed subscription metadata;
- deterministic deduplication keys;
- delivery attempts and bounded retries;
- dead-letter and explicit replay;
- correlation IDs for causal routing;
- read/write lifecycle separated from Platform authority.

Acceptance: duplicate publications with the same workspace/dedupe key resolve to one event, deliveries remain workspace-isolated, failed deliveries dead-letter at the configured limit, and replay returns dead letters to pending without executing handlers.


## M29 — Scheduler & Job Runtime

M29 adds the durable temporal runtime above the event/signal layer and below tasks/workflows.

### Scope

- cron, interval, one-shot and calendar schedules;
- IANA timezone validation and UTC-normalized persistence;
- deterministic schedule generation;
- generation-protected schedule updates;
- skip, run-once and bounded catch-up misfire policies;
- durable job records;
- deterministic job IDs;
- worker leases and expired-lease recovery;
- per-schedule maximum concurrency;
- bounded due-job queries;
- dispatcher failure persistence.

### Runtime model

```text
Schedule -> Job -> Task -> Workflow / Agent -> Platform Run
```

The scheduler owns temporal lifecycle and job state. It does not authorize consequential actions or create Platform authority. Dispatched work enters the existing OS lifecycle and governed Platform path.

### Acceptance

The M29 suite verifies cadence, cron/timezone behavior, catch-up, generation conflicts, concurrency limits, lease recovery and durable dispatcher failures.

### Distributed boundary

M29 is the durable single-node scheduler contract. Distributed workers, queue backends, leader election/fencing, regional scheduling and failover remain M38. This prevents SQLite from being presented as a distributed scheduler while preserving a replaceable scheduler persistence boundary.


## M30 — Context & Knowledge Fabric

Durable sources, documents and chunks with provenance, freshness, authority, classification and trust metadata; deterministic lexical retrieval; bounded context assembly; and a stable seam for future semantic/vector retrieval backends. Retrieval remains data and never becomes Platform authority.


## M31 — Connectors & Data Spaces

Connector lifecycle, endpoint validation, capabilities metadata and durable synchronization cursors across filesystem, Git, databases, object storage, HTTP/SaaS, messaging, knowledge and MCP data spaces. MCP remains the interoperability protocol; OS owns lifecycle around it.


## M32 — Resource, Cost & Capacity Runtime

M32 adds durable OS-observed resource accounting and cost attribution for model, compute, storage, network and tool/workflow usage. Quantities are integer values with explicit units and monetary values use integer micro-units to avoid floating-point accounting drift. Records can be attributed to workspace, agent, task and workflow.

M32 is accounting and telemetry, not an authorization or quota engine. Agent Platform remains authoritative for budgets, quotas, approvals and consequential execution. The ledger therefore records observed consumption and attributable cost; it cannot grant additional capacity, bypass a Platform budget, or turn a local estimate into authoritative billing.

### Acceptance

- durable usage records survive process restart;
- workspace/resource summaries are deterministic;
- cost attribution works at agent/task/workflow scope;
- invalid negative quantities/costs and naive timestamps fail closed;
- duplicate usage identifiers are rejected;
- no Platform authority is introduced.


## M33 — Evaluation & Agent Quality Runtime

M33 provides the repository-owned evaluation lifecycle above agent/workflow execution:

- versioned evaluation cases and suite identity;
- durable evaluation runs with workspace/agent/workflow/model attribution;
- integer metric measurements with explicit units and evidence references;
- deterministic regression gates with fail-closed missing/unit-mismatch behavior;
- baseline/candidate metric comparison;
- durable run completion state.

The runtime records and evaluates quality signals; it does not execute customer workloads, grant capabilities, authorize actions, enforce Platform budgets, or create authoritative evidence. FAS/FAS-Bench and future external benchmark providers can integrate through these contracts without becoming kernel dependencies.

### Acceptance

- evaluation cases and runs survive process restart;
- measurements are workspace/run/case attributable and duplicate-safe;
- gates pass only when an observed metric exists with the expected unit and threshold relation;
- baseline/candidate comparisons are deterministic;
- naive timestamps and invalid identities fail closed;
- no Platform authority is introduced.


## M34 — Enterprise Fleet & Remote Control Plane

M34 turns the M20 remote runtime seam into an explicit fleet control-plane contract.

### Scope

- durable device enrollment and inventory;
- endpoint identity metadata and attestation references;
- workspace-scoped fleet groups;
- deployment desired state with version and rollout cohort;
- device lifecycle states: enrolled, online, draining, offline, quarantined;
- generation-protected device updates;
- workspace-safe group membership;
- deterministic capacity-aware placement planning;
- rollout state records that can be consumed by external deployment workers.

### Boundary

M34 owns fleet composition and desired state. It does not implement a second identity/authorization system, grant capabilities, approve actions, execute customer code, or create authoritative evidence. Device attestation, hosted control-plane persistence, certificate lifecycle and remote management are integration seams.

### Acceptance

- devices and groups are durable and workspace isolated;
- stale device updates fail by generation conflict;
- group membership rejects workspace mismatch;
- deployment targets must belong to the same workspace as their group;
- placement excludes offline/draining/quarantined devices and respects capacity;
- no Platform authority is introduced.


## M35 — Device / Desktop Operating Environment

M35 defines the Tinlance-managed device deployment profile without turning the Agent OS repository into a Linux distribution.

### Scope

- device security profiles for Secure Boot, TPM, disk encryption and offline policy;
- verified OS image metadata with lowercase SHA-256 digests;
- architecture and boot-chain metadata;
- desired OS image state with generation protection;
- staged/active/failed/rollback update lifecycle;
- recovery-image references;
- durable device-local OS deployment state.

### Deployment model

The reference deployment is an image-based Linux environment with signed/verified boot artifacts, hardware-backed device identity and rollback-capable updates. Current atomic Linux ecosystems demonstrate the operational value of image-based updates and rollback, while newer sealed-image approaches combine Secure Boot, UKIs, composefs/fs-verity and TPM-backed disk unlock. M35 keeps those mechanisms as deployment implementations rather than hard-coding a distribution or boot stack.

### Boundary

M35 does not implement a kernel, bootloader, TPM service, encryption engine, package manager, fleet authorization system or remote execution authority. M34 handles fleet desired state; Agent Platform remains authoritative for identity, authorization, approvals and consequential execution.

### Acceptance

- device security profiles and image metadata are durable;
- image digests are strictly validated;
- desired image updates are generation protected;
- duplicate/no-op updates fail closed;
- update state transitions are generation protected;
- recovery image references remain explicit;
- no Platform authority is introduced.
