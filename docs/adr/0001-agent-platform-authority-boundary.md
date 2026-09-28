# ADR-0001: Agent Platform Is the Authority Boundary

## Decision

Tinlance Agent Platform remains the sole authority for consequential agent execution.

Agent OS is a higher-level operating environment. It manages intent, lifecycle, workspace,
session, task and presentation state but does not independently authorize side effects.

## Consequences

- Agent OS integrates through stable Platform contracts.
- Agent OS must not import Platform internals.
- Approvals are references to Platform decisions, not local authorization grants.
- Evidence from Platform remains authoritative.
- Domain systems such as FAS, FDSE and TADS are integrations, not core dependencies.
