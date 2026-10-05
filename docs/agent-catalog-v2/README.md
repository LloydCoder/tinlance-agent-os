
# Agent Catalog v2

Agent Catalog v2 is the semantic discovery and composition layer for Tinlance Agent OS.

It does not replace or duplicate Tinlance Agent Platform authority, M17 multi-agent coordination, M26 desired-state management, or M36 supply-chain registry semantics.

## Core rule

The catalog answers what exists, what it can do, and how it can be composed. The Platform answers what is authorized and what may execute.

~~~text
Goal
  |
  v
Task/context analysis
  |
  v
Capability Catalog
  |
  v
Capability matching
  |
  v
Agent selection
  |
  +--> single agent
  |
  +--> dynamic TeamSpec
          |
          v
      M17 coordination
          |
          v
   Platform authority
          |
          v
 Evidence / artifacts
~~~

## Frozen vocabulary

- Agent: an executable or addressable actor with identity and declared behavior.
- Capability: a governed semantic unit of work an agent can perform.
- Skill: a narrower behavior supporting a capability; descriptive unless bound to an agent.
- Role: an organizational or coordination position, not an authority grant.
- Archetype: a reusable behavioral pattern for selecting/composing agents.
- Tool: an operation surface; not an agent.
- Environment: execution/data context.
- Domain: subject-matter classification.
- Team: a runtime composition of agents around a goal.
- Workflow: a durable OS process definition whose steps may be executed by agents.
- Directory: desired-state declarations for agents.
- Catalog: semantic metadata and discovery for capabilities/agents.
- Registry: package/publisher/version and supply-chain metadata.
- Authority: effective permission to cause a consequential action; owned by Agent Platform.

## Non-negotiable invariants

1. Catalog metadata never grants authority.
2. Capability declarations are not capability grants.
3. Roles are not authorization boundaries.
4. Tools are not agents.
5. Workflows are not teams.
6. Teams are not authorization planes.
7. Child authority can never exceed parent authority.
8. Child team budget can never exceed remaining parent budget.
9. Cross-tenant and cross-workspace composition is rejected.
10. External agents must cross the authenticated Platform trust boundary before consequential execution.
11. Evidence provenance remains authoritative in Platform/FAS-integrated evidence systems.
12. A single-agent plan is preferred whenever sufficient.
13. The planner must not spawn agents merely because candidates exist.
14. Dynamic teams have bounded depth, fan-out, cardinality, runtime, retries and cost.
15. Catalog evolution is versioned and compatibility-checked.

## Relationship to external standards

A2A provides agent collaboration interoperability and Agent Card metadata for identity, capabilities, skills, interfaces and security requirements. Tinlance maps that metadata into its catalog but does not treat an Agent Card as an authority grant.

MCP is the tool/data integration layer. An MCP server is a tool provider, not automatically an agent.

NIST's 2026 AI Agent Standards Initiative emphasizes interoperability plus agent security and identity. OWASP's 2026 Agentic Applications guidance highlights inter-agent communication, cascading failure, supply-chain, memory/context and rogue-agent risks. These become catalog/planning constraints; enforcement remains in Platform.

## Serial build

Phase 0 freezes architecture and vocabulary. Implementation begins only after its gate is green.

0. Architecture freeze
1. Repository/contract forensics
2. Taxonomy reconciliation
3. External ecosystem research
4. Canonical ontology
5. Capability schema
6. Catalog storage/index
7. Catalog discovery API
8. Capability matching
9. Agent selection
10. Team specification
11. Dynamic team planner
12. Team composer/DAG
13. Governed team execution
14. Evidence/handoff/synthesis
15. A2A/MCP interoperability
16. Evaluation/benchmarking
17. Adversarial/security validation
18. Production hardening
19. GA/continuous discovery

Every phase requires implementation, tests, architecture/contract tests, documentation reconciliation, CI green and forensic review before the next phase.
