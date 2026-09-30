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
| M11 | Production / Distribution foundation | COMPLETE |\n| M12 | Agent Lifecycle Runtime | COMPLETE |

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
