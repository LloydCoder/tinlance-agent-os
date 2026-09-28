# ADR-0001: Agent Platform Is the Authority Boundary

## Decision

Tinlance Agent OS delegates consequential authorization and execution to
Tinlance Agent Platform.

## Rationale

The Agent Platform already implements the canonical authority chain, complete
mediation, approvals, budgets, sandboxing, evidence and governance. Duplicating
these controls in Agent OS would create divergent security semantics and a
second authority plane.

## Consequences

Agent OS may own user experience, task composition, scheduling and lifecycle
presentation. It must consume Platform decisions rather than reproduce them.
