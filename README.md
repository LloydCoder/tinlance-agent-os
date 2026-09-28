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
- confidential/restricted data fail-closed until a governed external provider is integrated;
- bounded search.

Sensitive agent memory is treated as a security boundary, not as an unrestricted key-value store.

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
├── domain.py             # OS domain contracts
├── contracts.py          # Platform-facing protocol
├── platform_adapter.py   # Platform mapping
├── transport.py          # Versioned transport
├── client.py             # Deterministic conformance double
├── daemon.py             # Local Unix-socket daemon
├── daemon_service.py     # OS lifecycle service
├── store.py              # Durable SQLite state
├── workflow.py           # Workflow definition/execution
├── memory.py             # Classified memory
├── applications.py       # Application manifests/lifecycle
├── system.py             # Filesystem/process/notification abstraction
├── shell.py              # Toolkit-neutral shell model
├── extensions.py         # Capability-scoped extension SDK
├── enterprise.py         # Remote/fleet integration seam
└── distribution.py       # Release/update integrity
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
- Roadmap: docs/ROADMAP.md
- M1 status: docs/M1-STATUS.md
- M2-M11 status: docs/M2-M11-STATUS.md
- M2-M11 architecture: docs/ARCHITECTURE-M2-M11.md
- Threat model: security/threat-model.md
- Security controls: docs/SECURITY-CONTROLS.md
- Architecture Decision Records: docs/adr/
- Contributing: CONTRIBUTING.md
- Security policy: SECURITY.md

---

## Status

**M0–M11 repository implementation: complete.**

"Complete" means the repository-owned contracts, implementation, tests, architecture constraints and documentation are implemented and verified by CI. External infrastructure is explicitly represented as an integration seam rather than being simulated or overstated.

## License

Apache-2.0. See LICENSE.
