# Agent OS M0-M1 Threat Model

## Scope
M1 adds the remote integration boundary between Agent OS and Agent Platform. Agent OS remains a composition and lifecycle layer; Agent Platform remains the authority and governed execution layer.

## Trust boundaries
User -> Agent OS -> authenticated Platform adapter -> Agent Platform -> tools/MCP/sandbox/external systems.

## Untrusted inputs
The OS treats model output, retrieved content, tool responses, external content, extension data, peer-agent messages and remote Platform response data as untrusted until validated against the typed OS contract.

## M1 controls
1. Agent OS never grants execution authority.
2. Tenant and subject context is immutable for a transport instance.
3. Each Platform operation receives a fresh request identifier.
4. Credentials are carried only in the Authorization header and excluded from payloads.
5. HTTPS is required for non-loopback endpoints.
6. Endpoint redirects are rejected to prevent credential forwarding.
7. Embedded endpoint credentials are rejected.
8. Non-idempotent side-effecting operations are never automatically retried.
9. Idempotent reads may retry only bounded transient failures.
10. Remote response version and shape are validated before conversion to OS objects.
11. Platform approval and evidence identifiers remain opaque references.
12. OS never re-implements Platform authorization, policy, approval or execution.
13. The API version and W3C trace context are validated at the wire boundary.
13. Architecture tests prevent direct Platform implementation imports.

## Threats
| Threat | Control |
|---|---|
| Cross-tenant confused deputy | Tenant is explicit, immutable and transported on every request |
| Credential leakage | Authorization header only; no redirects; no URL credentials |
| Duplicate side effects | No automatic retries for non-idempotent operations; Platform request IDs support server-side idempotency |
| Protocol downgrade/drift | API version mismatch fails closed |
| Malformed remote data | Strict response validation |
| Prompt injection / excessive agency | OS cannot convert model output into authority |
| Approval bypass | OS receives opaque approval references only |
| Evidence forgery | Platform remains evidence authority |
| Domain dependency escalation | Architecture tests block domain-product imports |
| Local task spoofing | Dispatch requires a previously persisted task whose identity matches the request |

## Residual risk
Production still requires the Platform's real authenticated gateway, short-lived scoped credentials, durable telemetry and operational controls. Agent OS does not attempt to recreate those controls.