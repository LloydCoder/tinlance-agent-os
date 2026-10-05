
# ADR-0005: Agent Catalog v2 and Dynamic Team Formation Boundary

Status: Accepted — Phase 0 architecture freeze.

## Context

Tinlance Agent OS already contains M17 multi-agent coordination, M26 desired-state agent directory management and M36 package/marketplace registry semantics. A separate catalog or team-formation repository would duplicate lifecycle, coordination or supply-chain boundaries.

The ecosystem still needs a semantic layer answering which capabilities exist, which agents implement them, which environments/modalities/protocols they support, which candidates satisfy a task, whether one agent is sufficient, and when a bounded team is warranted.

A2A defines Agent Cards for identity, capabilities, skills, interfaces and security requirements and supports catalog discovery. NIST's 2026 AI Agent Standards Initiative emphasizes interoperability, security and identity. OWASP's 2026 agentic guidance highlights inter-agent communication, cascading failures, supply-chain, memory/context and rogue-agent risks.

## Decision

Agent Catalog v2 is implemented inside Agent OS as a semantic discovery/planning subsystem.

There will be no separate tinlance-agent-catalog or tinlance-agent-team-formation repository.

Catalog v2 owns:

- canonical ontology;
- capability definitions and relationships;
- agent capability profiles;
- semantic discovery;
- capability matching;
- candidate ranking metadata;
- TeamSpec planning metadata;
- catalog provenance/evaluation metadata.

M17 owns authenticated coordination and durable parent/child task state.

M26 owns desired-state agent inventory.

M36 owns package/publisher/version supply-chain metadata.

Agent Platform owns identity, authorization, policy, approvals, budgets, secrets, sandbox/tool authority, governed execution and authoritative evidence/audit.

## Authority invariant

Catalog metadata can produce a candidate or plan but never a grant.

For every delegation:

~~~text
effective_child_authority is a subset of effective_parent_authority
~~~

Platform decides effective authorization.

## Team invariant

A team is a composition strategy, not an authority principal.

The planner must prefer a single-agent plan when the goal and constraints can be satisfied without collaboration.

Any team plan must declare bounded fan-out, depth, active agents, total agents, retries, runtime, token/tool budgets and cost ceilings.

## Compatibility

Catalog v2 contracts must remain consumable by M17/M26/M36 without changing their existing authority semantics. Platform contract changes require coordinated Platform-side conformance updates.

## Consequences

Positive:

- semantic discovery is separated from lifecycle and supply-chain concerns;
- dynamic team formation becomes first-class without duplicating M17;
- A2A/MCP can map into a stable internal model;
- the 420-agent taxonomy can be normalized without creating 420 permanent agents.

Negative:

- ontology and schema governance become explicit;
- matching/planning quality becomes an evaluation problem;
- external metadata remains untrusted and freshness-sensitive;
- team planning adds resource/cost and failure-mode complexity.

## Phase gate

Phase 0 is complete only after documentation, architecture tests and CI verify these boundaries.
