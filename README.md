# Tinlance Agentic OS

> An agent-native operating environment above the governed Tinlance Agent Platform.

Tinlance Agentic OS is the higher-level runtime and user environment for **people, agents, workspaces, sessions, tasks, workflows, applications, memory, system integration, extensions, remote agents, and lifecycle management**.

It is deliberately **not** a second authorization kernel.

> **Core invariant:** Agent OS composes intent and lifecycle; Agent Platform establishes authority and executes consequential actions.

[![CI](https://github.com/LloydCoder/tinlance-agent-os/actions/workflows/ci.yml/badge.svg)](https://github.com/LloydCoder/tinlance-agent-os/actions/workflows/ci.yml)
[![License](https://img.shields.io/badge/license-Apache--2.0-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.12%2B-blue.svg)](pyproject.toml)

---

## Why this project exists

Agentic software needs more than an LLM loop. A usable agent environment needs durable lifecycle state, session/task semantics, workflow composition, memory boundaries, application and extension contracts, local system integration, remote/fleet seams, release integrity, and a clear security model.

Tinlance Agentic OS provides those **OS-level composition primitives** while delegating consequential authority to the Tinlance Agent Platform.

This separation is intentional:

- **Agent OS** owns *what the environment is doing*: intent, lifecycle, workspace/session/task state, workflows, applications, presentation, and system abstractions.
- **Agent Platform** owns *what the environment is allowed to do*: identity, tenancy authorization, policy, approvals, budgets, governed execution, and authoritative evidence.
- **Domain products** such as FAS, FDSE, TADS, ThreatFade and Hezqara remain integrations, not kernel dependencies.

NIST's 2026 work on agent identity and authorization emphasizes identification, authorization, auditing, non-repudiation, and controls around agent actions. The architecture here keeps those consequential controls in one authoritative plane.

---

## Architecture

~~~text
                         Human / Organization
                                  |
                                  v
                    +---------------------------+
                    |   Tinlance Agentic OS     |
                    |---------------------------|
                    | Workspace / Session       |
                    | Task / Workflow           |
                    | Application / Extension   |
                    | Memory / Context          |
                    | Shell / System adapters   |
                    | Remote / Distribution     |
                    +-------------+-------------+
                                  |
                         governed adapter
                                  |
                                  v
                    +---------------------------+
                    | Tinlance Agent Platform   |
                    |---------------------------|
                    | Identity / Tenancy         |
                    | Authorization / Policy     |
                    | Approval / Budget          |
                    | Governed Execution        |
                    | Sandbox / Tool authority  |
                    | Evidence / Audit authority |
                    +-------------+-------------+
                                  |
                                  v
                     Tools / MCP / External APIs
~~~

### Authority boundary

The critical path is:

~~~text
user/agent intent
      -> OS task/workflow
      -> Platform request
      -> Platform authorization + policy + approval
      -> Platform governed execution
      -> Platform evidence/events
      -> OS lifecycle/presentation
~~~

Agent OS must never turn model output, retrieved content, memory, tool output, an extension request, or a remote response into authority.

This follows least-privilege and independent-authorization principles emphasized by OWASP for agent systems.

---

## Session is not Run

A foundational design decision:

- **Session** = interaction/lifecycle context in Agent OS.
- **Task** = unit of OS intent and lifecycle.
- **Platform Run** = governed execution instance in Agent Platform.

Therefore:

~~~text
one Session -> many Tasks
one Task    -> zero, one, or many Platform Runs
~~~

This prevents presentation/session lifecycle from becoming an accidental execution authority model.

---

## Roadmap

| Milestone | Scope | Status |
|---|---|---|
| M0 | Architecture Foundation | Complete |
| M1 | Agent Platform Adapter | Complete |
| M2 | Local Agent OS Daemon | Complete |
| M3 | Workspace + Sessions + Tasks | Complete |
| M4 | Workflow Engine | Complete |
| M5 | Context + Memory | Complete |
| M6 | Agent Application Model | Complete |
| M7 | System Integration | Complete |
| M8 | Desktop/Shell foundation | Complete |
| M9 | Extensions | Complete |
| M10 | Enterprise / Remote OS foundation | Complete |
| M11 | Production / Distribution foundation | Complete |
| M12 | Agent Lifecycle Runtime | Complete |
| M13 | Agent SDK / Application SDK | Complete |
| M14 | Model Gateway + Model Router | Complete |
| M15 | Context + Trusted Memory | Complete |
| M16 | Real Workflow Runtime | Complete |
| M17 | Multi-Agent Runtime | Complete |
| M18 | Agent Ecosystem Runtime | Complete |
| M19 | Agent Workspace & Channels | Complete |
| M20 | Local/Remote Agent Runtime | Complete |
| M21 | Agent OS Observability | Complete |
| M22 | Reference Agents | Complete |
| M23 | Agent OS Conformance & Red Team Suite | Complete |
| M24 | Production Agent OS | Complete |
| M25 | Enterprise Forensic Hardening | Complete |
| M26 | Agent Directory & Desired-State Management | Complete |
| M27 | Enterprise Workspace & Organization Fabric | Complete |
| M28 | Event, Signal & Reactive Runtime | Complete |
| M29 | Scheduler & Job Runtime | Complete |
| M30 | Context & Knowledge Fabric | Complete |
| M31 | Connectors & Data Spaces | Complete |
| M32 | Resource, Cost & Capacity Runtime | Complete |
| M33 | Evaluation & Agent Quality Runtime | Complete |
| M34 | Enterprise Fleet & Remote Control Plane | Complete |
| M35 | Device / Desktop Operating Environment | Complete |
| M36 | Agent Marketplace & Enterprise Registry | Complete |
| M37 | Enterprise Admin & Operator Plane | Complete |
| M38 | Reliability, HA, DR & Chaos | Complete |
| M39 | Enterprise Security, Compliance & Governance Integration | Complete |
| M40 | Agent OS Intelligence & Adaptive Runtime | Complete |
| M41 | Enterprise GA & Certification | Complete |

The roadmap is implemented as a **repository-level architecture and integration foundation**. M8-M11 intentionally expose provider/deployment seams rather than pretending that a desktop toolkit, hosted fleet control plane, enterprise IdP, telemetry backend, package registry, or signing service already exists inside this repository.

See docs/ROADMAP.md, docs/ARCHITECTURE.md, and docs/M2-M11-STATUS.md.

---

## Milestone implementation

### M0 — Architecture Foundation

- stable domain contracts;
- explicit Agent Platform authority boundary;
- Session vs Run separation;
- domain-product independence;
- threat model and ADRs;
- architecture tests;
- Python 3.12–3.14 CI.

### M1 — Agent Platform Adapter

- provider-neutral Platform client contract;
- versioned HTTP transport;
- immutable tenant/subject context;
- bearer authentication;
- HTTPS-by-default;
- redirect and embedded-credential rejection;
- bounded JSON responses;
- strict response validation;
- bounded retries only for explicitly idempotent reads;
- lifecycle, capability, approval, event, evidence and health mappings.

### M2 — Local Agent OS Daemon

- Unix-domain socket control surface;
- restrictive socket permissions;
- same-user peer enforcement where SO_PEERCRED is available;
- bounded line-delimited JSON protocol;
- request-size and request-time limits;
- controlled shutdown.

### M3 — Durable OS State

- SQLite-backed workspaces, sessions, tasks, events, memory and workflow state;
- foreign-key enforcement;
- WAL and full synchronous durability;
- indexes for common workspace/session/event access;
- explicit read/write API separation.

### M4 — Workflow Engine

- declarative workflow definitions;
- dependency validation;
- unknown-dependency and duplicate detection;
- cycle detection;
- deterministic ready-step calculation;
- execution lifecycle for start, complete, fail and cancel.

### M5 — Context + Memory

- workspace and scope isolation;
- explicit data classification;
- public/internal local persistence;
- versioned working/session/task/agent/long-term memory;
- provenance and integrity digests with version chains;
- public/internal/confidential/restricted classification;
- trust separation between trusted instructions, verified facts, untrusted content and quarantined content;
- workspace/agent/session/task retrieval isolation;
- retention and expiry with explicit deletion;
- compare-and-swap versioning and conflict rejection;
- deterministic poisoning detection and quarantine;
- trust-separated context assembly.

Sensitive agent memory is a security boundary, not an unrestricted key-value store. Confidential and restricted memory can persist locally, but retrieval is fail-closed unless the caller's classification ceiling explicitly permits it.

### M6 — Agent Application Model

- declarative manifests;
- capability requests;
- lifecycle states;
- duplicate/invalid manifest rejection;
- install/enable/disable/uninstall semantics.

### M7 — System Integration

- root-confined filesystem access;
- explicit executable allowlist;
- fixed trusted executable resolution;
- non-interactive subprocesses;
- timeout and process-group termination;
- notification abstraction.

The OS integration layer is intentionally not a general-purpose shell executor.

### M8 — Desktop/Shell Foundation

- toolkit-neutral shell command model;
- no GUI framework hard dependency;
- presentation remains above the authority plane.

### M9 — Extensions

- declarative capability requests;
- capability-scoped extension context;
- lifecycle start/stop;
- no duplicated authorization engine.

### M10 — Enterprise / Remote OS Foundation

- remote-agent registry;
- secure endpoint validation;
- online/offline/draining state;
- explicit integration seam for a future fleet/control plane.

### M11 — Production / Distribution Foundation

- content-addressed SHA-256 release verification;
- verified/staged/apply/rollback state machine;
- version binding between staged artifact and applied version.

For production distribution, cryptographic signing and build provenance should be supplied by deployment/signing infrastructure. SLSA describes provenance as verifiable information connecting an artifact to how and where it was produced.

---

## Security model

### Trust boundaries

~~~text
User
  |
  v
Agent OS
  |
  v
Authenticated Platform adapter
  |
  v
Agent Platform authority
  |
  +--> tools / MCP
  +--> sandbox
  +--> external systems
~~~

### Security invariants

1. Agent OS does not authorize consequential actions.
2. Platform identity and tenancy authority are authoritative.
3. Platform approvals are opaque references, not local grants.
4. Platform evidence remains authoritative.
5. Model output is never authorization.
6. External/retrieved/tool content is treated as untrusted input.
7. Non-idempotent Platform operations are not automatically retried.
8. Local daemon access is restricted to the owning user where supported.
9. Local filesystem access is root-confined.
10. Local process execution is allowlisted and cannot bypass the allowlist through absolute paths.
11. Confidential/restricted local memory fails closed.
12. Release artifacts are integrity-verified before staging.
13. CI third-party actions are pinned to immutable commit SHAs.

OWASP recommends least privilege, explicit authorization for sensitive operations, human approval for high-impact actions, bounded retries/tool chains, structured audit trails, and adversarial regression testing for agent systems.

---

## Observability

Agent OS models lifecycle/state occurrences as OS events and leaves authoritative execution evidence to Agent Platform.

OpenTelemetry recommends events for checkpoints, state changes and lifecycle moments, while duration-bearing operations are better represented as spans.

Production telemetry should correlate:

- tenant;
- subject;
- session;
- task;
- workflow;
- Platform run;
- event/correlation ID;
- application/extension identity;
- outcome/error metadata.

Sensitive prompts, credentials and confidential memory should not be emitted by default.

---

## What this repository is — and is not

### It is

- an agent-native OS composition layer;
- a local lifecycle/control daemon foundation;
- a durable workspace/session/task state layer;
- a deterministic workflow composition engine;
- a memory/context boundary;
- an application and extension model;
- a constrained system integration layer;
- a remote/fleet integration foundation;
- a release/update integrity state machine.

### It is not

- a replacement for Tinlance Agent Platform;
- an authorization or policy engine;
- a sandbox implementation;
- a model provider;
- a hosted enterprise IdP;
- a hosted fleet-control SaaS;
- a complete graphical Linux desktop;
- a package registry or signing service;
- an EDR/MDM/VPN replacement.

Those boundaries are deliberate.

---

## Repository layout

~~~text
src/tinlance_agent_os/
├── domain.py             # Core OS domain contracts
├── contracts.py          # Platform-facing protocol contracts
├── platform_adapter.py   # Agent Platform authority adapter
├── transport.py         # Versioned Platform transport
├── client.py             # Deterministic Platform conformance double
├── store.py              # Durable local state
├── daemon.py             # Local Unix-socket daemon
├── daemon_service.py     # OS lifecycle service
├── cli.py                # CLI control entry point
├── agent_runtime.py      # M12 agent lifecycle
├── agent_directory.py    # M26 desired-state agent directory
├── sdk.py                # M13 official Agent Developer SDK
├── model_gateway.py      # M14 model provider/router
├── workflow.py           # Workflow DAG contracts
├── workflow_runtime.py   # M16 durable workflow execution
├── coordination.py       # M17 multi-agent coordination
├── ecosystem.py          # M18 package/skill ecosystem boundary
├── memory.py             # M15 trusted memory/context
├── knowledge.py          # M30 knowledge fabric
├── applications.py       # Agent application manifests/lifecycle
├── system.py             # Filesystem/process/notification adapters
├── shell.py              # Toolkit-neutral shell model
├── extensions.py         # Capability-scoped extensions
├── workspace.py          # M19 channels/workspace presentation
├── workspace_fabric.py   # M27 organization/project/environment/workspace fabric
├── event_runtime.py      # M28 event/signal/reactive runtime
├── scheduler.py          # M29 temporal/job runtime
├── connectors.py         # M31 connector/data-space contracts
├── resource.py           # M32 resource/cost/capacity ledger
├── evaluation.py         # M33 evaluation/quality runtime
├── fleet.py              # M34 fleet/control-plane contracts
├── device_os.py          # M35 device/desktop OS profile
├── registry.py            # M36 agent registry/marketplace contract
├── operator.py            # M37 admin/operator plane
├── reliability.py         # M38 HA/DR/chaos contracts
├── enterprise_security.py # M39 enterprise security/compliance integrations
├── adaptive.py             # M40 adaptive optimization/recommendation runtime
├── assurance.py            # M41 GA release-assurance contracts
├── enterprise.py           # Remote/fleet integration seam
├── remote_runtime.py       # Local/remote worker runtime
├── observability.py        # OpenTelemetry lifecycle telemetry
├── reference_agents.py     # Canonical governed reference agents
├── production.py           # Production release controller
└── distribution.py         # Release/update integrity state machine
~~~

---
## Quick start

### Requirements

- Python 3.12+
- a supported Linux/macOS development environment for local execution;
- a real Agent Platform gateway for production integration.

### Install

~~~bash
python -m pip install -e ".[dev]"
~~~

### Run quality gates

~~~bash
ruff check .
ruff format --check .
mypy src
pytest --cov=tinlance_agent_os --cov-report=term-missing --cov-fail-under=85
pip-audit
~~~

### CLI

~~~bash
agentos --help
~~~

The CLI exposes the repository's control entry point; daemon and lifecycle services are Python APIs intended to be wired into a service manager/deployment runtime.

---

## Production integration boundary

A production deployment supplies the infrastructure deliberately kept outside this repository:

- authenticated Agent Platform gateway;
- short-lived/scoped credentials;
- enterprise identity/SSO;
- durable Platform evidence and telemetry;
- secret management;
- fleet/control-plane service;
- artifact repository;
- release signing and provenance/attestation;
- operating-system service management;
- desktop toolkit and shell integration where required.

This separation prevents the repository from claiming security properties that only the surrounding deployment can actually enforce.

---

## Engineering principles

- **Authority is singular.**
- **Identity is explicit.**
- **State is durable.**
- **Boundaries are typed.**
- **Untrusted content stays untrusted.**
- **Least privilege is the default.**
- **Side effects are explicit.**
- **Retries are semantics-aware.**
- **Security failures fail closed.**
- **Provider/deployment seams are explicit rather than simulated.**
- **Architecture constraints are tested, not merely documented.**

---

## Documentation

- Architecture: docs/ARCHITECTURE.md
- Agent Platform integration contract: docs/architecture/agent-platform-integration.md
- Roadmap: docs/ROADMAP.md
- M16 status: docs/M16-STATUS.md
- M1 status: docs/M1-STATUS.md
- M2-M11 status: docs/M2-M11-STATUS.md
- M2-M11 architecture: docs/ARCHITECTURE-M2-M11.md
- Threat model: security/threat-model.md
- Security controls: docs/SECURITY-CONTROLS.md
- Architecture Decision Records: docs/adr/
- Contributing: CONTRIBUTING.md
- Security policy: SECURITY.md

---

## Agent Developer SDK

M13 provides the supported developer surface for building agents without manipulating low-level Platform HTTP contracts directly.

Example shape:

~~~python
from tinlance_agent_os import AgentSDK, CapabilityDeclaration

app = sdk.scaffold(
    agent_id="research-agent",
    workspace_id="workspace-1",
    name="Research Agent",
    version="1.0.0",
    entrypoint="research.main",
    capabilities=(CapabilityDeclaration("research.read", "Read approved research sources"),),
)

runtime = app.runtime(store, handler)
runtime.register()
runtime.validate()
runtime.start()

session = sdk.session("workspace-1", user_id, app.scaffold.definition.agent_id)
task = sdk.task(session, "Research the requested subject")
result = sdk.execute(task)
~~~

The SDK provides typed scaffolding, lifecycle/session/task/workflow helpers, capability declarations, Platform-backed approval requests, execution/evidence results, structured errors, durable idempotency and execution-context propagation. It is deliberately not an authorization layer; the Agent Platform remains authoritative.

## Context + Trusted Memory

M15 replaces the original memory primitive with a durable security-aware subsystem. Memory records carry workspace/scope identity, provenance, classification, trust state, version, retention metadata and an integrity digest.

The subsystem separates working, session, task, agent and long-term memory, detects common persistent prompt-injection and exfiltration patterns before persistence, quarantines suspicious records, and assembles retrieval into separate trust channels. Untrusted retrieved content is never silently promoted to trusted instructions.

## Model Gateway + Router

M14 adds a provider-neutral model surface so agent logic does not depend on a vendor API:

~~~text
Agent -> Agent SDK -> Model Gateway -> Model Router -> Provider
~~~

The gateway supports provider abstraction, model registration, capability matching, deterministic routing, strict cost/latency/context/privacy policy, provider/model allowlists, transient fallback, decision models, embeddings and reranking. Hosted, private and local deployments use the same provider contract. Vision and speech are explicitly reserved for a later phase.

A reference agent calls `sdk.model(ModelRequest(...))`; switching the registered provider/model changes routing configuration rather than agent logic. Model output remains untrusted data and cannot grant Platform authority.

## Real Workflow Runtime

M16 turns the workflow DAG into a durable runtime. It persists workflow instances, step attempts, checkpoints, approvals, human-input pauses, retries, schedules and events. Independently ready branches can execute in parallel while retaining deterministic dependency semantics.

A consequential step receives one stable idempotency key for its lifetime. If the process crashes after the Platform side effect but before the OS checkpoint commits, recovery resumes the same logical step with the same key. The Agent Platform remains authoritative for execution and exactly-once/idempotency semantics; Agent OS never creates a second authority plane.

M16 acceptance coverage includes sequential and parallel execution, conditions, retries/backoff, deadlines, cancellation, approval and human-input pauses, compensation, crash recovery, event/schedule triggers and Platform Run mapping.

## Status

**M0–M29 repository implementation: complete.**

M23 adds an independent adversarial conformance suite. M24 adds the production release controller and signed distribution workflow. M25 closes the forensic-hardening gaps found after M24: release minimum-version enforcement and safe staging failure handling, trusted-memory provenance promotion controls, supervised-process environment hardening, Unix fleet endpoint validation, and immutable GitHub Action pin enforcement.

M26 adds the Agent Directory desired-state layer on top of the existing M12 lifecycle runtime. Desired state is durable and generationed; reconciliation is deterministic and read-only.

"Complete" means the repository-owned contracts, implementation, tests, architecture constraints and documentation are implemented and verified by CI. External infrastructure is explicitly represented as an integration seam rather than being simulated or overstated.


## Agent Catalog v2 and Dynamic Team Formation

Agent Catalog v2 is the semantic discovery and composition layer above M17, M26 and M36.

- M17 remains the authenticated multi-agent coordination runtime.
- M26 remains the desired-state Agent Directory.
- M36 remains the package/publisher/version and supply-chain Registry.
- Agent Platform remains the sole authority for identity, authorization, policy, approval, budget, governed execution and authoritative evidence.
- Catalog metadata never grants authority.

The catalog normalizes agents, capabilities, skills, roles, archetypes, tools, environments, domains, protocols, risk, autonomy and evaluation profiles. Dynamic team formation is a planning function: the planner chooses the least-complex valid plan and prefers a single agent when collaboration is unnecessary.

The full serial build is documented in docs/agent-catalog-v2/README.md. Phase 0 architecture is frozen in docs/agent-catalog-v2/ARCHITECTURE.md and ADR-0005.

The design aligns with current agent interoperability and security direction: A2A Agent Cards describe identity/capabilities/skills/interfaces and support registry/catalog discovery; NIST's 2026 AI Agent Standards Initiative emphasizes interoperability, security and identity; OWASP's 2026 agentic guidance includes inter-agent communication, cascading failure, supply-chain, memory/context and rogue-agent risks.

## License

Apache-2.0. See LICENSE.


## Multi-Agent Runtime

M17 provides supervisor/child-agent coordination with durable task ownership, authenticated identities, signed message envelopes, tenant/workspace isolation, delegated-capability subset checks, shared trace continuity, result aggregation and cancellation propagation.

The coordinator is not an authority plane. Identity and capability verification are explicit integration contracts, while the Agent Platform remains authoritative for grants, policy, approvals, execution and evidence.


## Agent Ecosystem Runtime

M18 provides a verified package boundary for skills, applications, extensions, connectors and agents: artifact hashes, signatures, provenance, dependency resolution, quarantine, rollback and Platform-backed capability grants.

### M19 — Agent Workspace & Channels

M19 provides the unified presentation plane for the OS:

- Web
- CLI
- Desktop
- API
- Messaging
- Notifications

All six use the same durable ChannelRuntime. A channel carries the workspace and, when bound, the same session/task/agent identity and lifecycle trace. Handoffs therefore change presentation surface without creating a new lifecycle or authority plane.

The workspace surface is:

text
Workspace
 ├── Agents
 ├── Applications
 ├── Skills
 ├── Sessions
 ├── Tasks
 ├── Workflows
 ├── Memory
 ├── Integrations
 └── Events

This milestone defines the protocol/runtime boundary; it does not pretend that a specific GUI framework, messaging provider or hosted web frontend is embedded in the Python core.

### M20 — Local/Remote Agent Runtime

M20 adds a supervised local/remote runtime layer:

- process supervision;
- resource limits;
- root-bound filesystem bindings;
- network endpoint policy;
- authenticated remote enrollment;
- endpoint identity and heartbeats;
- reconnect/offline/draining/disconnect lifecycle;
- deterministic workspace fleet routing;
- remote task assignment and cancellation;
- Platform Run mapping with stable idempotency;
- MCP transport interoperability.

The remote runtime is a worker plane, not an authority plane. Consequential work still enters through the Agent Platform, where identity, tenancy, capabilities, authorization, policy, approvals, execution and evidence remain authoritative.

MCP is used as an interoperability transport rather than replaced by a Tinlance-specific remote protocol. The current MCP direction uses a stateless core with explicit mechanisms/extensions for stateful and long-running work, so Agent OS keeps its durable lifecycle state in its own store. citeturn1search10turn1search12


## Observability and Reference Agents

M21 provides OpenTelemetry traces/metrics with OTLP configuration and W3C context propagation. M22 provides the canonical Research, Cybersecurity, FDE/Engineering and World Intelligence agents, all routed through the same Agent OS + SDK + Platform governed execution path.


## Production Distribution

M24 adds signed release artifacts, CycloneDX SBOMs, Sigstore signing, GitHub artifact attestations, staged channels, health-gated deployment, automatic rollback, downgrade prevention, migration/backup controls and operational security runbooks.

### M27 — Enterprise Workspace & Organization Fabric

M27 adds durable organizational context above the existing workspace/session/task runtime. It models organization → project → environment → workspace relationships, workspace configuration inheritance, templates, lifecycle state and generation-protected workspace binding. It does not implement authorization; Agent Platform remains authoritative for identity and access.

The configuration model follows a layered approach: organization defaults → project overrides → environment overrides → workspace overrides. Effective configuration is deterministic and exportable. Cross-organization/project/environment bindings fail closed, and concurrent workspace changes use generation checks.

### M28 — Event, Signal & Reactive Runtime

M28 adds durable workspace-scoped event publication, subscriptions, delivery state, deduplication, bounded retry/dead-letter handling and replay. Events are lifecycle/data signals; they never grant authority or execute consequential actions.


### M29 — Scheduler & Job Runtime

M29 adds the durable temporal runtime above the event/signal layer:

- cron, interval, one-shot and calendar schedules;
- IANA timezone validation with UTC-normalized persistence;
- generation-protected schedule updates;
- explicit skip/run-once/catch-up misfire policy;
- deterministic job IDs and durable job state;
- worker leases with expiry/recovery;
- per-schedule concurrency limits;
- bounded due-job queries and durable dispatcher failures.

The runtime follows:

```text
Schedule -> Job -> Task -> Workflow / Agent -> Platform Run
```

The scheduler controls *when* OS work becomes a job. It does not authorize work, mint capabilities, approve actions or create authoritative evidence. Distributed queues, leader election/fencing, multi-node scheduling and regional failover remain M38.

See docs/M29-STATUS.md for acceptance and operational boundaries.


### M30 — Context & Knowledge Fabric

M30 adds durable knowledge sources, documents and chunks; provenance, freshness, authority, classification and trust metadata; deterministic retrieval; and bounded context assembly. Knowledge is data, not authority, and retrieval cannot grant Platform permissions.

See docs/M30-STATUS.md for the acceptance boundary.


### M31 — Connectors & Data Spaces

M31 provides durable connector registration, endpoint validation, connector lifecycle state and synchronization cursors for external data spaces. Connector metadata is not authority; consequential operations still cross Agent Platform governance.


### M32 — Resource, Cost & Capacity Runtime

The resource ledger records OS-observed usage and attributable cost metadata for workspace, agent, task and workflow reporting. It uses durable SQLite state, explicit units and integer micro-costs. It does not enforce or replace Agent Platform budgets, quotas or authorization.


### M33 — Evaluation & Agent Quality Runtime

M33 provides a durable evaluation surface for agent and workflow quality: versioned cases, run records, metric measurements, deterministic regression gates and baseline/candidate comparisons. Measurements use explicit units and integer values; missing or mismatched units fail gates closed. Evaluation results are evidence for engineering decisions, not authorization, billing, policy or Platform authority. External benchmark suites such as FAS/FAS-Bench can integrate through these contracts without becoming Agent OS kernel dependencies.


### M34 — Enterprise Fleet & Remote Control Plane

M34 adds the repository-owned fleet control-plane contract: durable device inventory, workspace-scoped fleet groups, desired agent deployment records, rollout cohorts, device health/draining/quarantine states and deterministic capacity-aware placement planning. It is a control-plane seam, not a replacement for Agent Platform authorization, identity or governed execution. Hosted control-plane services, attestation providers and device-management infrastructure remain deployment integrations.


### M35 — Device / Desktop Operating Environment

M35 defines the device-side deployment profile for Tinlance-managed Linux systems: security posture, verified OS image metadata, desired image state and staged/active/rollback lifecycle. The repository owns the contract and local state model; boot firmware, Secure Boot keys, TPM, disk encryption, image builders and device-management services remain deployment integrations. Atomic/image-based Linux approaches provide a useful reference for rollback-oriented device updates, but M35 does not embed a distribution in the Python core.


### M36 — Agent Marketplace & Enterprise Registry

M36 adds a durable package registry contract for publishers, packages and versions, including artifact digests, signature/provenance/SBOM references, compatibility metadata, quarantine/revocation state and generation-safe lifecycle changes. The registry never executes package code or grants capabilities; installation remains subject to deployment policy and Agent Platform authority.


### M37 — Enterprise Admin & Operator Plane

M37 adds a durable operational projection and command-intent surface for the Agent OS control center. It can represent agent/workflow/fleet/model/event projections and operator intents while preserving source-of-truth ownership in the underlying runtimes. Consequential actions remain governed dispatches rather than local operator authority.


### M38 — Reliability, HA, DR & Chaos

M38 adds enterprise reliability contracts for deployment profiles, worker leases, disaster-recovery plans and controlled chaos scenarios. Local SQLite remains a valid single-node profile; distributed PostgreSQL, durable queues, worker orchestration, regional failover and backup infrastructure remain deployment implementations rather than duplicated kernel services.


### M39 — Enterprise Security, Compliance & Governance Integration

M39 adds durable integration contracts for enterprise identity providers, KMS/HSM providers, audit export, data residency/retention/legal hold and incident response. These are integration states and evidence-oriented control records; Agent Platform remains the authoritative identity, authorization and governance plane.

### M40 — Agent OS Intelligence & Adaptive Runtime

M40 adds a durable adaptive layer that converts observed runtime metrics into explainable optimization recommendations for model routing, workflow routing, context optimization, resource routing, fleet placement, retry tuning and remediation.

The adaptive layer is deliberately **non-authoritative**:

- observations are workspace-scoped and unit-explicit;
- recommendations carry the policy, observed value, target and evidence-oriented reason;
- recommendations use generation checks for operator decisions;
- no recommendation grants a capability, changes a Platform budget, approves an action or executes customer work;
- accepted recommendations remain intents for the owning runtime to validate and dispatch through the normal governed path.

This gives Agent OS a controlled feedback loop without turning optimization into a second policy or execution kernel.


### M41 — Enterprise GA & Certification

M41 closes the repository roadmap with a release-assurance contract rather than a claim of external certification. It records release identity, API/schema compatibility, artifact/SBOM/provenance references and evidence-backed CI, security, performance, chaos, disaster-recovery, compliance and supply-chain checks.

External certification and assurance activities remain external: a repository record cannot itself establish SOC 2, ISO 27001, penetration-test completion or customer-specific compliance. SLSA requires provenance to identify build outputs by cryptographic digest and describes increasing guarantees for provenance authenticity and integrity; the release pipeline therefore keeps provenance and SBOM references explicit. NIST CSF 2.0 is used as an organizational mapping reference across Govern, Identify, Protect, Detect, Respond and Recover.

M41 is complete when the repository can express and evaluate these release gates deterministically; production organizations must still execute their own external assurance program.
