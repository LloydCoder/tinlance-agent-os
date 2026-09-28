# Agent OS Security Boundary

## Core rule

Agent OS is a composition and interaction layer, not an authority engine.

Consequential actions must be authorized and executed through Tinlance Agent
Platform. Agent OS must never infer authority from model output, retrieved content,
tool output, memory, task state or UI state.

## Trust boundaries

1. Human input -> Agent OS.
2. Agent OS -> Agent Platform.
3. Agent Platform -> models/tools/MCP/sandbox.
4. External systems -> Agent Platform.

## Untrusted data

- model output
- retrieved content
- tool responses
- external content
- peer-agent messages
- extension-generated content
- persisted memory

## Security invariants

- OS task state never grants Platform authority.
- Platform approvals remain Platform-owned.
- Platform evidence remains Platform-owned.
- Tenant and principal authority cannot be widened by OS state.
- Secrets are not copied into ordinary OS context or task metadata.
- Agent Platform internal modules are not imported by OS packages.
