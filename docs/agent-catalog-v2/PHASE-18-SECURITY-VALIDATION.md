# Phase 18 — Adversarial and Security Validation

## Threat model

| Threat | Required invariant | Validation |
|---|---|---|
| Agent identity spoofing | principal identity is authenticated | M23 red-team + Platform identity |
| Cross-tenant delegation | tenant/workspace cannot change through child creation | M23 + delegation tests |
| Capability escalation | child capability set is a subset of parent | delegation tests |
| Budget/fanout explosion | bounded TeamBudget | TeamBudget + planner tests |
| Recursive/cyclic execution | DAG rejects cycles and unknown edges | TeamGraph tests |
| Memory/context poisoning | untrusted memory remains quarantined | M23 red-team |
| Inter-agent impersonation | sender identity is authenticated | M23 red-team |
| Supply-chain tampering | artifact hash/signature verification | M23 red-team |
| Remote endpoint spoofing | endpoint identity is verified | M23 red-team |
| Protocol metadata abuse | A2A/MCP metadata cannot grant authority | Catalog security suite |
| Evidence overclaiming | confidence is bounded and evidence refs remain explicit | handoff tests |
| Secret leakage | telemetry excludes sensitive payloads by default | M23 red-team |

## External security alignment

NIST's 2026 agent standards initiative emphasizes interoperability, identity/authentication and security. OWASP's 2026 Agentic Applications framework explicitly covers identity/privilege abuse, insecure inter-agent communication, cascading failures, supply-chain vulnerabilities, memory/context poisoning and rogue agents.

A2A Agent Cards are discovery metadata describing identity, interfaces, capabilities, security requirements and skills; signatures can protect integrity. They are not local authorization grants.

MCP 2026-07-28 adds discovery, authorization hardening and Tasks while using a stateless protocol core. MCP protocol metadata remains a compatibility/integration input; Platform remains the authorization boundary.

## Phase 18 gate

Phase 18 is complete only when:

- adversarial Catalog/team tests pass;
- existing M23 red-team suite passes;
- all supported Python CI matrices are green;
- architecture-boundary checks are green;
- dependency audit is green;
- no Catalog API exposes authorization/approval/execution authority;
- documentation and threat model are reconciled.

## References

- https://www.nist.gov/artificial-intelligence/ai-agent-standards-initiative
- https://genai.owasp.org/resource/owasp-top-10-for-agentic-applications-for-2026/
- https://a2a-protocol.org/v1.0.1/specification/
- https://blog.modelcontextprotocol.io/posts/2026-07-28/
