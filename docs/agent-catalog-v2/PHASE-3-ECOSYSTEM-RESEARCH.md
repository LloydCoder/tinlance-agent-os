# Phase 3 — External Ecosystem Research and Reconciliation

Status: Phase 3 implementation baseline.

Audit date: 2026-10-05.

## Adopted external facts

### A2A

Current A2A documentation defines Agent Cards as discovery metadata containing identity, endpoint/interface information, protocol capabilities, security requirements and skills. Current A2A also supports discovery through well-known Agent Cards, registries/catalogs and direct configuration, plus signed Agent Cards and authenticated extended cards.

**Tinlance adoption**

- Agent Card maps into an external-agent profile.
- Agent skill maps into descriptive skill metadata.
- A2A protocol version is a compatibility constraint.
- A2A security schemes become connection requirements, not local authority.
- Agent Card signatures become provenance/integrity signals.
- Extended cards remain authenticated data.
- External A2A execution must re-enter Platform authority.

### MCP

The final 2026-07-28 MCP revision introduced a stateless protocol core, discovery, authorization hardening, Tasks, extensions and conformance-oriented evolution. MCP's current conformance matrix tracks the 2026-07-28 revision.

**Tinlance adoption**

- MCP server = tool/data provider, not automatically an agent.
- MCP tool = tool capability input to matching.
- MCP protocol version = compatibility constraint.
- MCP auth metadata = connection requirement.
- MCP Tasks may inform long-running tool/task modeling but do not replace M17.
- MCP authorization never replaces Platform authorization.

### NIST

NIST's 2026 AI Agent Standards Initiative is organized around industry standards, community protocols and research into agent identity/authentication/security.

**Tinlance adoption**

Catalog v2 therefore treats identity, authentication, authorization, auditability, interoperability and security as first-class profile dimensions. NIST is guidance/reference material, not an execution authority.

### OWASP / AIUC-1

The 2026 OWASP agentic security framework and AIUC-1 crosswalk identify agent-specific risks including goal hijacking, tool misuse, identity/privilege abuse, memory poisoning, insecure inter-agent communication, cascading failures, trust exploitation, supply-chain issues and rogue agents.

**Tinlance adoption**

These become catalog risk attributes, evaluation dimensions and team-planning constraints. Enforcement remains Platform/M24/R10.

## Framework ecosystem mapping

| Ecosystem pattern | External pattern | Tinlance decision |
|---|---|---|
| OpenAI Agents SDK | manager/agents-as-tools and handoffs | adopt as orchestration pattern vocabulary; add governance and durable team semantics |
| Microsoft Agent Framework | agents, workflows, harness agents, graph orchestration, checkpoints | adopt as comparative workflow/team model; keep M17/Platform authority boundary |
| A2A | remote agent discovery and collaboration | adopt as interoperability protocol |
| MCP | tool/data integration and discovery | adopt as tool protocol |
| LLM-only supervisor loops | model chooses arbitrary subagents | constrained planner; bounded and policy-admitted |
| Graph workflow engines | explicit DAG/graph execution | map to TeamSpec topology; M17 remains runtime |
| Crew/swarm abstractions | peer/team composition | map to bounded TeamSpec; no unconstrained swarm authority |
| Computer-use agents | UI/browser/desktop actions | model as modality/environment/tool requirements |
| Voice agents | audio interaction | model as modality plus latency/reliability constraints |
| Multimodal agents | image/audio/video/document I/O | model as modalities and capability requirements |
| Robotics/physical agents | physical-world actuation | model as high-risk environment/capability; approval and stronger Platform policy |
| Agent marketplaces | packages/skills/agents | M36 remains supply-chain authority; Catalog consumes trusted metadata |
| Academic agent taxonomies | role/task/skill categorizations | use as semantic input; canonical Tinlance ontology remains authoritative |

## Architectural conclusions

1. Discovery metadata is not authorization.
2. Agent skills are useful semantic discovery units but do not replace canonical capabilities.
3. A2A and MCP are complementary: A2A describes agent-to-agent interaction; MCP describes tool/data integration.
4. Current frameworks commonly expose either handoff routing, manager-style delegation or explicit workflow graphs. Tinlance needs all three as bounded planning topologies.
5. Enterprise agent composition requires identity, provenance, policy, budgets, cancellation, audit and recovery beyond basic framework-level handoffs.
6. External protocols must be version-pinned and conformance-tested.
7. Catalog records must preserve source protocol, version, provenance and freshness.
8. External metadata can inform trust scoring but cannot grant local authority.
9. The semantic ontology must not be tied to one framework or model provider.
10. Computer use, voice, multimodal and physical-world agents are modalities/environments, not separate authorization planes.

## Sources

- A2A definitions: https://a2a-protocol.org/latest/definitions/
- A2A discovery: https://a2a-protocol.org/latest/topics/agent-discovery/
- A2A v1.0.1 specification: https://a2a-protocol.org/v1.0.1/specification/
- MCP 2026-07-28 release: https://blog.modelcontextprotocol.io/posts/2026-07-28/
- MCP conformance matrix: https://plan.modelcontextprotocol.io/matrix
- NIST AI Agent Standards Initiative: https://www.nist.gov/artificial-intelligence/ai-agent-standards-initiative
- OWASP Top 10 for Agentic Applications 2026: https://genai.owasp.org/resource/owasp-top-10-for-agentic-applications-2026/
- OpenAI Agents SDK orchestration: https://openai.github.io/openai-agents-python/multi_agent/
- Microsoft Agent Framework: https://learn.microsoft.com/en-us/agent-framework/overview/

## Phase 3 exit decision

External categories are mapped to adoption, integration, constraint or rejection.

No external framework becomes a dependency of Catalog v2's canonical ontology.

No external metadata source receives implicit authority.

Phase 4 may proceed to canonical ontology design.
