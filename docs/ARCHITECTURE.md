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


## M16 Durable Workflow Runtime

M16 is the OS control-plane workflow runtime. It owns workflow state, scheduling, dependency readiness, checkpoints and recovery; it does not become an execution authority.

### State model

```text
CREATED -> RUNNING
RUNNING -> CHECKPOINTED -> RUNNING
RUNNING -> WAITING_APPROVAL -> RUNNING
RUNNING -> WAITING_INPUT -> RUNNING
RUNNING -> RETRY_WAIT -> RUNNING
RUNNING -> COMPENSATING -> FAILED
RUNNING -> COMPLETED
RUNNING -> CANCELLING -> CANCELLED
RUNNING -> FAILED
```

Workflow definitions are validated for duplicate IDs, unknown dependencies and cycles before an instance can start. Independently ready steps may execute in parallel; dependency readiness remains deterministic.

### Consequential-action invariant

Each instance/step receives a deterministic idempotency key. The key is persisted before the executor is called and never changes across retries or crash recovery. The Platform adapter receives that same key when creating the Platform Run. This closes the common crash window between an external side effect and local checkpoint commit without pretending that the OS can provide exactly-once semantics on its own.

### Pause/resume

Approval and human-input gates are durable state transitions. The process can exit while a workflow is waiting; a later process reads the persisted instance and resumes from the checkpoint. Approval validity and authorization remain Platform-owned.

### Recovery

A process interruption can leave a step marked RUNNING. Recovery treats that state as an interrupted attempt, returns it to PENDING while retaining its original idempotency key, and resumes the workflow. Completed steps are never selected again.

### Triggers

The runtime supports manual, event and schedule triggers. Schedules are durable records with a next-run timestamp; a scheduler integration calls the runtime to materialize due instances. Cron interpretation and fleet scheduling remain deployment seams.

### Authority boundary

```text
Workflow Runtime
  | state / dependency / retry / checkpoint / recovery
  v
Agent Platform adapter
  | create/cancel/request-approval with stable idempotency key
  v
Platform authority
  | identity / tenancy / policy / capability / approval / execution
  v
Run / tool / evidence
```

The workflow runtime never mints capabilities, approves itself, bypasses Platform policy, or treats workflow metadata as authorization.

### Local durability

The current repository implementation uses SQLite with WAL and short transactions. SQLite permits concurrent readers but serializes writers; the runtime therefore uses optimistic workflow-instance versions and keeps each state transition small. A production multi-node scheduler remains an external deployment concern.


## M17 Multi-Agent Runtime

The coordination runtime preserves the authority boundary through every agent hop.

```text
Supervisor Agent
   |
   | authenticated identity + owned parent task
   v
Coordinator
   | tenant/workspace check
   | capability subset verification
   | durable child task
   | signed message + trace
   v
Child Agent
   |
   v
Agent Platform authority
```

### Identity

Every coordination principal is authenticated before it can create or own coordination state. Tenant and workspace are carried in the durable task and message envelope and are checked on delegation, send, receive and aggregation.

### Anti-spoofing

Agent messages contain a payload digest, nonce, sequence, sender/recipient identity, task identity and trace identifier. The complete envelope is authenticated with a signing adapter. The repository supplies HMAC for local deterministic tests; production identity/key management remains a Platform/deployment responsibility.

### Delegation

A supervisor can delegate only to an authenticated child in the same tenant/workspace. Requested capabilities are passed to an explicit verifier and must remain within the supervisor's declared capability set. These references are not grants; Platform authorization remains authoritative.

### Propagation

Child tasks retain the parent task ID and trace ID. Cancellation walks the durable task tree and marks active descendants cancelled. Result aggregation accepts only children owned by the requesting supervisor and tenant.

No agent message, child task or delegated capability creates Platform authority.


## M18 Agent Ecosystem Runtime

Packages are treated as untrusted supply-chain inputs until artifact hash and signature verification succeed. Dependency resolution is deterministic and version-exact. A package can be quarantined independently of its manifest. Capability requests are metadata; a separate Platform-backed grant is required before a package can receive authority.

## M19 Workspace + Channels

M19 introduces a unified presentation/channel plane:

text
                         Workspace
                             |
              +--------------+--------------+
              |              |              |
           Agents        Sessions        Tasks
              |              |              |
              +--------------+--------------+
                             |
                    unified ChannelRuntime
                             |
     +---------+------+-----+------+-----------+
     |         |      |     |      |           |
    Web       CLI  Desktop API  Messaging  Notifications
                             |
                             v
                    same OS lifecycle IDs
                    same trace continuity
                             |
                             v
                    Platform authority

ChannelRuntime is a routing/presentation abstraction. It does not authorize actions, mint capabilities, validate approvals as authority, or execute consequential operations.

Channel bindings are workspace-scoped. A handoff can bind an unbound target channel to an existing session/task/agent and copies the established lifecycle trace. If a target channel is already bound, its lifecycle identity and trace must match the source before handoff is accepted.

Channel envelopes retain workspace, session, task, agent and trace identifiers and are persisted as presentation events. This allows Web -> CLI -> Desktop -> API or messaging/notification transitions without creating a second session/task lifecycle.

The desktop channel is intentionally a protocol adapter, not a claim that a GUI toolkit is bundled. Concrete Web/API/messaging/desktop transports remain integration surfaces above this stable contract.

## M20 Local + Remote Agent Runtime

M20 adds a supervised compute/runtime plane beneath the OS lifecycle but above the Platform authority boundary.

    Agent OS
       |
       +-- Local Process Supervisor
       |      +-- resource limits
       |      +-- filesystem binding
       |      +-- process lifecycle
       |
       +-- Remote Endpoint
              +-- enrollment/identity
              +-- heartbeat/fleet state
              +-- network policy
              +-- MCP transport
                       |
                       v
                Agent Platform adapter
                       |
                       v
                Platform authority

### Local supervision

LocalProcessSupervisor is responsible for bounded process lifecycle. ResourceLimits are host-enforced where the operating system exposes the relevant controls. The OS never turns a resource limit into a Platform authorization decision.

FilesystemBinding produces the existing root-confined LocalSystemBackend. It therefore reuses the established filesystem security boundary instead of creating a second path policy.

NetworkPolicy admits only explicitly approved secure endpoint schemes/hosts and rejects private/loopback/link-local IP literals by default. It is a connection policy, not a substitute for Platform authorization.

### Remote enrollment and identity

Every endpoint has:

- stable endpoint ID;
- workspace and tenant binding;
- endpoint fingerprint;
- authenticated enrollment;
- address/protocol metadata;
- heartbeat timestamp;
- lifecycle state.

Heartbeat and reconnect re-authenticate the endpoint. Stale endpoints transition to OFFLINE; draining endpoints remain known but are excluded from new assignment; disconnect is explicit.

### Fleet routing

Routing is deterministic within a workspace: only authenticated HEALTHY endpoints are eligible, and candidates are ordered by latest heartbeat and stable endpoint ID. Cross-workspace assignment is rejected before remote transport.

### Remote execution

Remote assignment first obtains a Platform Run using the stable remote idempotency key remote:<task_id>. Only after the Platform has accepted the consequential operation is the remote transport invoked. This ordering prevents a remote endpoint from creating an independent authority path.

Remote cancellation invokes both the remote transport cancellation and the authoritative Platform Run cancellation. Remote transport results are untrusted operational data.

### MCP integration

M20 deliberately does not define a Tinlance-specific JSON-RPC replacement for MCP. MCPRemoteTransport maps remote assignment/cancellation to MCP tools/call through an injected MCP client. Current MCP specifications are moving toward a stateless core and explicit extensions/handles for long-running work; therefore durable Agent OS state remains in the OS store rather than being hidden inside an MCP transport session. citeturn1search10turn1search12

The transport adapter can later negotiate the MCP Tasks extension for servers that expose long-running task handles. That extension requires authentication/authorization checks on task operations and intentionally avoids an unscoped task list. citeturn1search1turn1search6

### Authority invariant

A remote agent is a worker/runtime endpoint, not an authority issuer:

    Remote endpoint
       -> OS remote runtime
       -> Platform Run
       -> Platform authorization/policy/approval
       -> governed execution
       -> Platform evidence

The remote endpoint cannot mint capabilities, substitute an identity, approve itself, or create authoritative evidence.


## M21/M22 Operational and Reference-Agent Boundary

OpenTelemetry is the telemetry substrate; Tinlance-specific identifiers are attached only as low-cardinality attributes where needed for lifecycle correlation. W3C trace context is propagated across lifecycle boundaries without recording sensitive payload content by default. Reference agents compose the existing SDK, memory/context, model gateway, skills and Platform adapter; they cannot turn model or skill output into authorization.


## M24 Production Distribution Boundary

The production distribution layer verifies external supply-chain evidence before activation. Sigstore/Cosign provides artifact signatures; GitHub artifact attestations provide signed SLSA/in-toto provenance and SBOM attestations; the runtime consumes those proofs through explicit verifier interfaces. Rollout, migration, backup, health and rollback state are durable operational controls and do not create a second execution authority.
