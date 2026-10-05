
# Agent Catalog v2 Terminology

This glossary is normative for Catalog v2.

| Term | Normative meaning | Not to be confused with |
|---|---|---|
| Agent | Identified actor/executable service that can perform work | capability, package |
| Agent instance | Runtime instance of an agent definition | package version |
| Capability | Semantic unit of work an agent can perform | authority/grant |
| Skill | Narrow behavior supporting a capability | permission |
| Role | Coordination/organizational position | authority |
| Archetype | Reusable agent behavior/profile pattern | concrete agent |
| Tool | Operation surface exposed by a provider | agent |
| Environment | Execution/data context | tenant |
| Domain | Subject-matter classification | role |
| Agent profile | Versioned semantic declaration of capabilities and constraints | Platform identity |
| Catalog | Semantic metadata/discovery system | registry |
| Directory | Desired-state inventory and lifecycle intent | catalog |
| Registry | Package/publisher/version/supply-chain inventory | directory |
| Team | Runtime composition of agents around a goal | workflow |
| TeamSpec | Versioned declaration of team composition/topology/bounds | authorization |
| Workflow | Durable OS lifecycle graph | team |
| Plan | Proposed composition/execution structure | authority decision |
| Delegation | Bounded task request from one agent to another | capability grant |
| Delegation envelope | Proposed bounded execution context inherited by a child | Platform authority |
| Authority | Effective permission to cause consequential action | capability |
| Evidence reference | Opaque reference to authoritative evidence | finding |
| Observation | Recorded fact/measurement before interpretation | evidence |
| Finding | Analyzed statement supported by evidence | verdict |
| Verdict | Decision/assertion from governed analysis | observation |
| Provenance | Information connecting artifact/evidence to origin and transformation | confidence |
| Trust state | Assessment of source/metadata acceptability for a purpose | authority |
| Evaluation profile | Versioned quality/security evidence | authority |
| Protocol | Interoperability contract such as A2A or MCP | capability |
| Modality | Input/output interaction type | protocol |
| Constraint | Requirement/ceiling applied during discovery/planning | permission |
| Policy | Authoritative rule governing execution | catalog metadata |
| Approval | Authoritative Platform decision/reference | planner intent |

## Naming rules

- Stable identifiers use lowercase dot-separated namespaces.
- Canonical names are unique within their ontology namespace.
- Aliases resolve to one canonical ID.
- Renames preserve stable IDs and create explicit alias/deprecation records.
- Capability IDs describe work, not permission.
- Role IDs must not imply privilege.
- Provider/package identifiers are not capability IDs unless explicitly modeled.

## Versioning

Ontology, schemas and profiles are independently versioned. Any change that alters interpretation of existing records requires a compatibility decision and migration path.

## Authority rule

No glossary term is an implicit authority grant. Capability, skill, role, archetype, team, TeamSpec, Agent Card, MCP tool and evaluation profile are descriptive/planning data until Platform admission and authorization.
