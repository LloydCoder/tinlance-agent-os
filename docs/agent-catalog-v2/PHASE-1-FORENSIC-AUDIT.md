
# Phase 1 — Repository and Contract Forensics

Status: Implemented audit baseline.

Audit date: 2026-10-05.

## Scope

This phase audits the live Tinlance Agent OS, Tinlance Agent Platform and official Platform SDK boundaries before Catalog v2 implementation. The purpose is to classify every relevant existing surface as:

- REUSE — directly consumed;
- EXTEND — existing contract remains authoritative but needs a compatible extension;
- REPLACE — existing implementation is semantically incorrect for the new contract;
- MISSING — required Catalog v2 capability is absent;
- FORBIDDEN_DUPLICATE — must not be implemented because another subsystem owns it.

## Existing implementation findings

### Agent OS M17

Observed existing responsibilities:

- authenticated agent principals;
- durable parent/child task ownership;
- same-tenant and same-workspace enforcement;
- capability-subset verification;
- signed agent messages/digests;
- sender/recipient anti-spoofing;
- monotonic sequencing;
- trace continuity;
- supervisor-scoped aggregation;
- cancellation-tree propagation.

Disposition: REUSE. Catalog v2 supplies semantic candidates and team plans; M17 remains the coordination runtime.

### Agent OS M26

Observed existing responsibilities:

- durable agent definitions;
- generation-protected updates;
- compatibility metadata;
- rollout metadata;
- lifecycle intent;
- observed state;
- deterministic reconciliation.

Disposition: REUSE. Catalog references M26 desired-state records; it does not create another directory.

### Agent OS M36

Observed existing responsibilities:

- publishers;
- packages;
- versions;
- artifact digests;
- signatures;
- provenance;
- SBOM references;
- compatibility;
- quarantine;
- revocation;
- lifecycle state.

Disposition: REUSE. Catalog consumes trust/provenance state; it does not become a package registry.

### Agent Platform M8/R10

Observed authoritative responsibilities:

- identity and tenant binding;
- authorization;
- policy;
- approvals;
- budgets/limits;
- sandbox/tool boundary;
- secrets boundary;
- governed execution;
- evidence;
- audit;
- idempotency;
- fail-closed execution.

Disposition: FORBIDDEN_DUPLICATE for Catalog. Catalog can propose requirements and bounded delegation envelopes but Platform decides effective authority.

### Agent Platform M17 interoperability

Observed contract:

- remote agent discovery metadata is descriptive;
- credential-free Agent Card metadata;
- secure transport and authorization;
- authority-attenuating remote delegation;
- consequential remote action re-enters Platform authorization/policy/approval/R10.

Disposition: REUSE/EXTEND at adapter boundary only.

### Agent Platform SDK

Observed developer surface:

- AgentSpec;
- declarative CapabilityDeclaration;
- typed EvidenceReference;
- lifecycle/observability metadata;
- MCP metadata;
- typed execution/approval contracts;
- explicit statement that declarations never grant authority.

Disposition: REUSE. Catalog profile schema may map into SDK declarations, but the SDK remains authority-neutral.

## Catalog v2 gap matrix

| Contract area | Existing owner | Disposition | Catalog v2 work |
|---|---|---|---|
| Agent identity | Platform/OS | REUSE | reference principal/definition |
| Desired agent inventory | M26 | REUSE | directory join |
| Package trust | M36 | REUSE | trust/provenance join |
| Capability semantics | partial declarations | MISSING | canonical ontology |
| Skill semantics | A2A/SDK descriptive fields | MISSING | normalized skill model |
| Domain taxonomy | scattered metadata | MISSING | canonical domain/family model |
| Environment support | partial metadata | MISSING | normalized environment constraints |
| Modality | A2A/SDK partial | EXTEND | common modality model |
| Protocol support | A2A/MCP metadata | EXTEND | protocol capability model |
| Agent capability profiles | partial SDK AgentSpec | EXTEND | canonical profile binding |
| Catalog persistence | no semantic catalog | MISSING | durable catalog/index |
| Capability discovery | partial registry/metadata | MISSING | discovery API |
| Constraint matching | no catalog matcher | MISSING | deterministic matcher |
| Agent selection | M17 coordination only | MISSING | selection engine |
| Single-vs-team decision | M17 execution only | MISSING | planner |
| TeamSpec | M17 task hierarchy only | MISSING | first-class planning contract |
| Team topology | M17 hierarchy | EXTEND | plan topology maps to M17 |
| Team budget model | Platform budget authority | EXTEND | proposed team budget, Platform enforcement |
| Delegation envelope | Platform authority | EXTEND | proposal only; Platform admission |
| Handoff schema | evidence/task refs exist | MISSING | structured handoff |
| Synthesis/review | no semantic synthesis contract | MISSING | reviewer/synthesizer layer |
| Evidence provenance | Platform/FAS | REUSE | evidence references only |
| A2A discovery | Platform interoperability | EXTEND | catalog adapter |
| MCP discovery | SDK metadata | EXTEND | tool requirement metadata |
| Evaluation profile | M33/Platform evaluation | EXTEND | catalog quality metadata |
| Team evaluation | no catalog team benchmark | MISSING | team benchmark suite |
| Security threat metadata | Platform M24 | EXTEND | risk profile joins |
| Authority enforcement | Platform R10 | FORBIDDEN_DUPLICATE | no local grants |
| Runtime coordination | M17 | FORBIDDEN_DUPLICATE | no second coordinator |
| Package registry | M36 | FORBIDDEN_DUPLICATE | no second registry |
| Desired-state directory | M26 | FORBIDDEN_DUPLICATE | no second directory |

## Required Catalog v2 implementation surface

The audit identifies these missing semantic components:

1. canonical ontology;
2. machine-readable capability schema;
3. durable catalog storage and indexes;
4. agent capability profiles;
5. catalog discovery API;
6. deterministic capability matcher;
7. agent selection engine;
8. TeamSpec;
9. dynamic team planner;
10. team composition/DAG adapter;
11. governed delegation envelope proposal;
12. structured handoff;
13. reviewer/synthesis contract;
14. A2A catalog adapter;
15. MCP capability/tool adapter;
16. catalog/team evaluation profiles.

These are the minimum semantic additions. Existing runtime authority is reused rather than rebuilt.

## External contract reconciliation

A2A's current specification describes Agent Cards containing agent identity, service endpoint, A2A capabilities, security requirements and skills; Agent Cards can be discovered through well-known locations, registries/catalogs or direct configuration. Signatures can protect cards, and sensitive cards should be access-controlled.

MCP 2026-07-28 is a final protocol revision with a stateless core, discovery RPC, authorization hardening, Tasks extension and formal conformance coverage. Catalog v2 therefore models MCP as a protocol/tool provider surface and stores protocol-version compatibility explicitly rather than treating MCP servers as agents.

NIST's 2026 AI Agent Standards Initiative prioritizes interoperable standards/protocols and research into agent identity, authentication and security. OWASP's 2026 Agentic Applications framework and AIUC-1 crosswalk emphasize agent identity/privilege abuse, insecure inter-agent communication, cascading failures, supply-chain risks, memory poisoning and rogue agents. Catalog metadata will expose relevant risk/evaluation dimensions; Platform remains the enforcement boundary.

## Phase 1 exit decision

No existing implementation requires replacement.

No new repository is justified.

No Platform authority contract must be moved into Agent OS.

Catalog v2 proceeds as an additive semantic layer inside Agent OS, with explicit integration points into M17/M26/M36 and Platform R10.
