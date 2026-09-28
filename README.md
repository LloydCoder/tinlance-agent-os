# Tinlance Agentic OS

An agent-native operating environment built on the governed Tinlance Agent Platform.

## Purpose
Agent OS is the higher-level environment where people, agents, workspaces, tasks, workflows and applications operate. It does not replace the Agent Platform authority kernel.

**Core invariant:**
> Agent OS composes intent and lifecycle; Agent Platform establishes authority and executes consequential actions.

## Architecture
Human -> Tinlance Agentic OS -> Versioned Agent Platform adapter -> Tinlance Agent Platform -> Tools / MCP / sandbox / external systems

Agent Platform is the authoritative governed execution substrate. Domain products such as FDSE, FAS, TADS and ThreatFade remain integrations rather than OS core dependencies.

## M0 and M1 status
M0 establishes the OS domain model, security boundary, session/run separation, architecture tests and CI foundation.

M1 adds the governed Platform adapter with versioned transport, tenant/subject/trace propagation, bearer authentication, HTTPS and redirect hardening, lifecycle/agent/capability/approval/event/evidence integration, bounded idempotent retries, strict response validation and compatibility tests.

See docs/M1-STATUS.md, docs/ARCHITECTURE.md, docs/ROADMAP.md and the ADRs.

## Security boundary
Agent OS never grants authority. Model output, retrieved content, memory, tool output and remote data cannot authorize consequential actions. Platform approvals and evidence are opaque references; Platform performs the authoritative checks and execution.

## Roadmap
M2 is the local Agent OS daemon. It should consume the M1 adapter rather than create a second transport or authority implementation.