
# Agent Catalog v2 Architecture Freeze

Status: Phase 0 — Architecture Frozen

## Ownership model

| Concern | Owner | Catalog role |
|---|---|---|
| Agent identity | Agent Platform / OS identity integration | reference |
| Agent lifecycle | Agent OS M12 | reference |
| Desired agent deployment state | M26 Directory | reference |
| Package/version supply chain | M36 Registry | reference |
| Capability semantics | Agent OS Catalog v2 | authoritative semantic model |
| Agent discovery | Agent OS Catalog v2 | authoritative discovery |
| Team planning | Catalog/Planner | plan only |
| Team coordination | M17 | execute coordination |
| Workflow lifecycle | M16 | execute workflow lifecycle |
| Authorization/policy | Agent Platform | authoritative |
| Approval | Agent Platform | authoritative |
| Budgets/limits | Agent Platform | authoritative enforcement |
| Governed execution | Agent Platform R10 | authoritative |
| Evidence/audit | Agent Platform | authoritative |

## Four distinct planes

### Agent Directory

M26 answers: which agents should exist in a workspace/environment?

It stores desired state, lifecycle intent and compatibility metadata.

### Agent Catalog

Catalog v2 answers: what capabilities and semantic profiles are available?

It stores canonical capability ontology, agent profiles, relationships, constraints, evaluation metadata and discovery indexes.

### Agent Registry / Marketplace

M36 answers: which packages, publishers and versions are distributable and trusted?

It stores artifact digests, signatures, provenance, SBOM references, compatibility and supply-chain state.

### Agent Platform authority

Platform answers: what is this principal allowed to do right now?

It is authoritative for identity, authorization, policy, approval, budget, sandbox/tool authority, execution and evidence/audit.

No plane may impersonate another.

## Agent vs capability

A capability is the semantic unit used for discovery and planning.

An agent is an implementation/actor exposing one or more capabilities.

~~~text
Domain
  -> Capability Family
      -> Capability
          -> Skill
              -> Agent Profile
                  -> Agent Instance
~~~

A capability may have multiple implementations. An agent may implement multiple capabilities. A role/archetype may influence selection but is not executable authority.

## Team vs workflow

A workflow is a durable OS control-plane definition describing lifecycle, dependencies, checkpoints and recovery.

A team is a composition of agents selected to achieve a goal.

A workflow may contain team tasks. A team may execute tasks outside a single workflow. Neither creates authorization.

## Data flow

~~~text
User / upstream task
       |
       v
Goal + constraints + context
       |
       v
Capability requirements
       |
       v
Catalog discovery
       |
       v
Constraint/risk/evaluation matching
       |
       +---- sufficient single agent ----> Agent Selection
       |
       +---- collaboration required ----> Team Planner
                                      |
                                      v
                                  TeamSpec
                                      |
                                      v
                                   M17 DAG
                                      |
                                      v
                              Platform admission
                                      |
                                      v
                              Governed execution
                                      |
                                      v
                           Evidence / artifacts
                                      |
                                      v
                               Review/synthesis
~~~

The catalog never crosses from discovery into authority. Platform admission is an explicit trust boundary.

## Authority attenuation

For delegation:

Authority(child) is a subset of Authority(parent).

For nested teams:

Authority(member) is a subset of Authority(supervisor).
Budget(child) is less than or equal to remaining Budget(parent).

The OS planner may propose an attenuation envelope. Platform validates and enforces effective authority.

## Team safety bounds

Every TeamSpec supports ceilings for maximum total agents, active agents, delegation depth, fan-out, retries, runtime, tool calls, tokens and cost, plus cancellation propagation, failure isolation and synthesis/review requirements.

Unset production limits are not interpreted as unlimited.

## Planning modes

The planner chooses the least-complex plan satisfying the goal:

1. SINGLE_AGENT
2. SEQUENTIAL
3. PARALLEL
4. HIERARCHICAL
5. DAG
6. REVIEW_LOOP
7. HUMAN_ESCALATION

A team is not formed merely because multiple agents match.

## Evidence model

Catalog and coordination use references, not authoritative evidence claims.

FAS semantics remain:

~~~text
observation != evidence != finding != verdict
~~~

Child handoffs may contain observations, evidence references, findings, artifacts, confidence and unresolved questions. Final synthesis retains provenance to source evidence/artifacts.

## Interoperability

A2A Agent Cards are external capability/skill metadata and must be validated before admission. A2A defines Agent Cards containing identity, capabilities, skills, interfaces and security requirements and supports catalog discovery.

MCP servers are tool/data providers. MCP metadata can contribute tool requirements to capability matching, but an MCP server is not automatically an agent.

External agents never receive local authority merely because metadata matches a catalog query. Consequential execution crosses the authenticated Platform trust boundary.

## Threat model implications

Catalog v2 explicitly addresses capability spoofing, stale metadata, agent impersonation, delegation laundering, recursive spawning, fan-out/token/cost storms, cross-tenant composition, malicious package metadata, supply-chain compromise, prompt/context poisoning, forged inter-agent messages, cascading failures and provenance loss.

Discovery metadata reduces uncertainty but cannot establish authority.

## Phase 0 exit criteria

- terminology frozen;
- ownership boundaries explicit;
- trust boundaries explicit;
- catalog/registry/directory separation explicit;
- agent/capability/team/workflow distinctions explicit;
- authority attenuation explicit;
- evidence semantics explicit;
- interoperability strategy explicit;
- architecture tests enforce negative boundaries;
- docs and roadmap reconciled;
- CI green.
