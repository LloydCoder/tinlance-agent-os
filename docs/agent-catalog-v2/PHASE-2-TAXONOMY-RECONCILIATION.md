# Phase 2 — 420 Seed Taxonomy Reconciliation

Status: Phase 2 implementation baseline.

## Canonical decision

The original 420 entries are the **Tinlance Agent Taxonomy v1 seed**, not 420 mandatory deployed agents.

The reconciliation unit is a governed semantic capability/agent profile. Each seed entry is normalized into one of:

- CAPABILITY
- SKILL
- ROLE
- ARCHETYPE
- META
- EVIDENCE
- CONTROL
- PROTOCOL

The catalog does not instantiate every taxonomy entry.

## Category reconciliation

| # | Seed category | Count | Canonical treatment |
|---:|---|---:|---|
| 1 | Core Platform / Reference Agents | 12 | META/CAPABILITY/ROLE; platform control behaviors remain existing Platform/OS surfaces |
| 2 | Cybersecurity | 45 | CAPABILITY; canonicalize duplicate Cyber Threat Intelligence into Threat Intelligence |
| 3 | FAS / Evidence Intelligence | 9 | EVIDENCE primitives + CAPABILITY; verdict is analytical output, never authority |
| 4 | FDSE / Software Engineering | 31 | CAPABILITY/ROLE; compose into software-engineering capability graph |
| 5 | FDE Mastery | 9 | CAPABILITY family |
| 6 | Tinlance World Intelligence | 20 | CAPABILITY/ROLE |
| 7 | TADS / Demand & Account Intelligence | 17 | composable signal CAPABILITYs |
| 8 | GTM / Revenue Intelligence | 18 | CAPABILITY |
| 9 | FadeReach | 9 | CAPABILITY |
| 10 | Olvrix / CRM & Automation | 12 | CAPABILITY/ROLE |
| 11 | Healthcare | 16 | CAPABILITY/ROLE |
| 12 | Fintech | 14 | CAPABILITY |
| 13 | Logistics & Supply Chain | 12 | CAPABILITY |
| 14 | Procurement | 10 | CAPABILITY |
| 15 | LegalTech | 10 | CAPABILITY |
| 16 | AI Governance | 14 | CAPABILITY integrated with Platform governance/evaluation |
| 17 | Data Engineering | 16 | CAPABILITY |
| 18 | Cloud & Infrastructure | 13 | CAPABILITY; Cloud Security canonicalizes to existing cybersecurity capability |
| 19 | DevSecOps | 10 | CAPABILITY; duplicate Container/Infrastructure Security canonicalized |
| 20 | IT Operations | 11 | CAPABILITY |
| 21 | Research & Knowledge | 12 | CAPABILITY; compose with intelligence capabilities rather than duplicate them |
| 22 | Finance & Business | 12 | CAPABILITY/ROLE; executive titles never imply privilege |
| 23 | Marketing | 10 | CAPABILITY |
| 24 | Customer Support | 10 | CAPABILITY |
| 25 | Executive & Operations | 11 | ROLE/CAPABILITY; CEO/COO/Chief of Staff are non-privileged roles |
| 26 | HR & People | 9 | CAPABILITY |
| 27 | Documents & Knowledge Assets | 9 | CAPABILITY |
| 28 | Compliance & Risk | 10 | CAPABILITY |
| 29 | Agent Infrastructure | 13 | existing OS/Platform control-plane functions + discovery/protocol capabilities; do not duplicate controls |
| 30 | Meta-Agents | 16 | META/control behaviors, not 16 permanent agent classes |

## Explicit canonical merges

| Seed entry | Canonical target | Reason |
|---|---|---|
| Cyber Threat Intelligence Agent | Threat Intelligence Agent | semantic duplicate; retain one canonical capability |
| Cloud Security Agent | Cloud Security capability under cybersecurity | cross-domain implementation, not a second authority |
| Container Security Agent in DevSecOps | Container Security capability | duplicate of cybersecurity capability |
| Infrastructure Security Agent in DevSecOps | Infrastructure Security capability | duplicate of cybersecurity capability |

Canonical IDs preserve historical aliases/deprecation metadata. No historical seed identifier is silently reused for a different meaning.

## Agent Infrastructure reconciliation

The following seed concepts are existing control-plane concerns, not new agent classes:

- Agent Registry Agent -> M36 registry/control surface
- Agent Discovery Agent -> Catalog discovery capability
- Agent Configuration Agent -> OS configuration/lifecycle
- Agent Lifecycle Agent -> OS lifecycle
- Agent Deployment Agent -> OS/deployment control plane
- Agent Monitoring Agent -> OS observability
- Agent Evaluation Agent -> evaluation subsystem
- Agent Observability Agent -> observability subsystem
- Agent Cost Optimization Agent -> resource/cost subsystem
- Agent Security Agent -> Platform/OS security controls
- Agent Identity Agent -> Platform identity
- Agent Permission Agent -> Platform authorization
- Agent Interoperability Agent -> A2A/MCP protocol capability

These are mapped, not recreated.

## Meta-agent reconciliation

Agent Architect, Builder, Planner, Router, Coordinator, Delegator, Reviewer, Critic, Judge, Evaluator, Optimizer, Memory Manager, Context Manager, Swarm Coordinator, Governance Supervisor and Agent-of-Agents are treated as reusable orchestration behaviors.

They may be represented as archetypes, planner strategies, roles or capabilities depending on execution context. They do not imply privileged authority and do not require permanent runtime agents.

## Taxonomy invariants

1. Every seed category is accounted for.
2. No seed entry creates a second authorization plane.
3. No seed entry creates a second M17 coordinator.
4. No seed entry creates a second M26 directory.
5. No seed entry creates a second M36 registry.
6. Duplicate semantics map to one canonical capability with aliases.
7. Roles do not imply privilege.
8. Evidence concepts do not become decision authority.
9. Meta behaviors are composable rather than mandatory agents.
10. The final deployed-agent count is intentionally not equal to 420.

## Exit state

Unresolved taxonomy classifications: **0**.

The reconciled seed is now ready to feed Phase 4 ontology design after Phase 3 external ecosystem research.
