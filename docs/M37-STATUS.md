# M37 — Enterprise Admin & Operator Plane

## Status

**Complete** — durable operator projections, workspace-scoped queries, generation tracking, command intents, tests and documentation are implemented.

## Boundary

The control center is a projection and intent surface. It does not become the source of truth for runtime state and does not directly execute consequential operations. Operator commands must dispatch through the owning runtime and Agent Platform authority.

## Acceptance

- projections are durable and workspace scoped;
- generations advance deterministically;
- command intents are unique and parameter-digest bound;
- naive timestamps fail closed;
- no second authorization or execution plane is introduced.
