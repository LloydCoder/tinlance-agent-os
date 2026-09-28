# Tinlance Agentic OS

An agent-native operating environment built on the governed Tinlance Agent Platform.

## Purpose

Agent OS is the higher-level environment where people, agents, workspaces, tasks,
workflows and applications operate. It does not replace the Agent Platform authority
kernel.

**Core invariant:**

> Agent OS composes intent and lifecycle; Agent Platform establishes authority and
> executes consequential actions.

## Architecture

```
Human
  |
  v
Tinlance Agentic OS
  |  workspaces / sessions / tasks / workflows / apps
  v
Agent Platform adapter
  |
  v
Tinlance Agent Platform
  |  identity / authorization / policy / approval / execution / evidence
  v
Tools / MCP / sandbox / external systems
```

Agent Platform is the authoritative governed execution substrate. Domain products such
as FDSE, FAS, TADS and ThreatFade remain integrations rather than OS core dependencies.

## M0 status

M0 establishes:

- provider-neutral OS domain contracts
- Platform adapter contract and deterministic conformance client
- session/run separation
- security threat model
- dependency-boundary architecture tests
- CI foundation
- architecture ADRs

M1 will add the transport-backed Agent Platform adapter.

## Roadmap

See [docs/ROADMAP.md](docs/ROADMAP.md) and [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).
