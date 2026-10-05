# Agent Catalog v2

Agent Catalog v2 is the semantic discovery, selection and dynamic-team planning layer inside Tinlance Agent OS.

It does not replace or duplicate M17 multi-agent coordination, M26 desired-state management, M36 package/marketplace registry semantics, or Agent Platform authority.

## Authority rule

The catalog answers:
- what capabilities and agents exist;
- which constraints they advertise;
- which candidates fit a goal;
- whether a bounded single-agent or team plan is appropriate.

Agent Platform answers:
- who the principal is;
- which tenant/workspace it belongs to;
- what is authorized;
- which policies and approvals apply;
- what may execute;
- what evidence/audit is authoritative.

Catalog metadata never grants authority.

## Canonical ontology

Domain -> Capability Family -> Capability -> Skill -> Agent Profile -> Agent Instance

Roles and archetypes are orthogonal semantic nodes. Tools, environments, modalities and protocols are typed discovery constraints.

## Serial build status

| Phase | Scope | Status |
|---:|---|---|
| 0 | Architecture freeze | COMPLETE |
| 1 | Repository/contract forensics | COMPLETE |
| 2 | 420 taxonomy reconciliation | COMPLETE |
| 3 | External ecosystem research | COMPLETE |
| 4 | Canonical ontology | COMPLETE |
| 5 | Capability schema | COMPLETE |
| 6 | Catalog storage/index | COMPLETE |
| 7 | Agent capability profiles | COMPLETE |
| 8 | Catalog discovery API | COMPLETE |
| 9 | Capability matching | COMPLETE |
| 10 | Agent selection | COMPLETE |
| 11 | Team specification | COMPLETE |
| 12 | Dynamic team planner | COMPLETE |
| 13 | Team composer/DAG | COMPLETE |
| 14 | Governed team execution boundary | COMPLETE |
| 15 | Evidence/handoff/synthesis | COMPLETE |
| 16 | A2A/MCP interoperability | COMPLETE |
| 17 | Evaluation/benchmarking | COMPLETE |
| 18 | Adversarial/security validation | COMPLETE |
| 19 | Production hardening | COMPLETE |
| 20 | GA/continuous discovery | IN PROGRESS |

## Catalog / Directory / Registry separation

- M26 Directory: desired-state inventory and lifecycle intent.
- Catalog v2: semantic capability metadata, profiles, discovery and planning.
- M36 Registry: publisher/package/version and supply-chain state.
- M17: authenticated coordination and durable parent/child task execution.
- Agent Platform: authoritative identity, authorization, policy, approval, budget, governed execution and evidence/audit.

## Dynamic team formation

The planner must choose the least-complex valid plan:

1. SINGLE_AGENT
2. SEQUENTIAL
3. PARALLEL
4. HIERARCHICAL
5. DAG
6. REVIEW_LOOP
7. HUMAN_ESCALATION

A team is not created merely because multiple candidates exist. TeamSpec bounds total agents, active agents, depth, fan-out, runtime, retries, tokens, tool calls and cost. Team graphs are validated against those limits before M17 coordination.

## Continuous discovery

External metadata is freshness-sensitive and untrusted.

Each discovery source records:
- stable source ID;
- source type/protocol;
- provenance;
- TTL;
- last refresh;
- enabled state.

Freshness can reduce candidate confidence or exclude stale metadata. Refresh cannot move backward in time. Discovery does not grant authority.

## Interoperability

A2A Agent Cards are mapped as external agent metadata. Current A2A defines Agent Cards with identity, interfaces, capabilities, skills and security requirements and supports discovery through well-known resources, registries/catalogs and direct configuration.

MCP is modeled as tool/data integration. MCP servers are not automatically agents. Protocol versions and authorization metadata are compatibility/security inputs, not local authority.

## Evidence

Catalog records references to authoritative evidence rather than creating verdict authority.

FAS semantics remain:

observation != evidence != finding != verdict

## Taxonomy

The original 420 entries are the Tinlance Agent Taxonomy v1 seed. The Phase 2 reconciliation accounts for all 420 entries across 30 categories with zero unresolved classifications.

The 420 figure is therefore a historical seed count, not a claim that exactly 420 permanent agents must be deployed.

## Phase gate

Every phase requires implementation, unit tests, contract/security tests, documentation reconciliation and green CI before merge. The merged main commit is revalidated before the next phase begins.

See ARCHITECTURE.md, TERMINOLOGY.md, OWNERSHIP.md and POST-MERGE-FORENSIC-AUDIT.md.
