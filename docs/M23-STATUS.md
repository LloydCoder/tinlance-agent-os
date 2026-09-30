# M23 — Agent OS Conformance & Red Team Suite

M23 is the adversarial acceptance layer for Agent OS. It does not merely prove that intended workflows succeed; it attempts to violate the architecture's security invariants.

## Attack taxonomy

| Area | Adversarial objective |
|---|---|
| Identity | spoofed/unauthenticated agent identity |
| Tenant | cross-tenant and cross-workspace escape |
| Capability | forged grants and delegation escalation |
| Approval | replay/idempotency and authority confusion |
| Idempotency | duplicate consequential execution |
| Workflow | cycle/state manipulation |
| Memory | persistent prompt injection / poisoning |
| Context | classification and context leakage |
| Tools | malicious skill/metadata cannot mint authority |
| Extensions | package capability escalation |
| Agents | inter-agent impersonation |
| Remote | endpoint spoofing and identity replay |
| Secrets | secret-like data absent from default telemetry |
| Recovery | crash between side effect and durable checkpoint |
| Supply chain | artifact/signature tampering |
| Distribution | downgrade/same-version update abuse |
| Observability | malformed trace context is not authority |

## Conformance rule

Each case is an attack attempt. A passing test means the attempted invariant violation was rejected or safely contained.

The suite is intentionally independent of FAS, FAS-Bench, ThreatFade and other Tinlance products. It tests Agent OS contracts directly.

The taxonomy follows current OWASP Agentic Application concerns including identity/privilege abuse, tool misuse, agentic supply-chain vulnerabilities, memory/context poisoning and insecure inter-agent communication. OpenTelemetry W3C trace context is treated as propagation metadata, not authorization.