# Agent OS ↔ Agent Platform Adapter Contract

## Status
Canonical Agent OS integration contract for Platform API v1.1.

Agent OS owns sessions, tasks, workflows, applications, workspace lifecycle and presentation. Agent Platform owns identity, tenancy authority, authorization, policy, approvals, budgets, governed execution, tool/MCP authority, sandbox/security boundaries and authoritative evidence.

## Wire contract

POST /v1/agent-platform

Required headers:
- Authorization: Bearer credential
- Content-Type: application/json
- X-Tinlance-API-Version: 1.1
- X-Request-ID: fresh non-empty identifier

Optional: traceparent using W3C Trace Context.

Body:
- tenant_id
- subject_id
- operation
- payload

The adapter propagates tenant and subject context but never treats those fields as authority. The Platform must bind them to the authenticated principal.

## Supported operations

- principal.get
- agents.list
- capabilities.list
- runs.create
- runs.cancel
- approvals.request
- runs.events
- runs.evidence
- health

Agent OS converts responses into typed OS references only after strict schema and API-version validation.

## Reliability

Only explicitly idempotent operations are automatically retried. Consequential run creation, cancellation and approval requests use deterministic request IDs so retries across transport attempts or OS restarts address the same logical request. Durable exactly-once side effects remain a Platform deployment responsibility.

Request IDs may be used by the Platform for server-side idempotency, but Agent OS must not claim exactly-once side effects unless the deployed Platform provides durable idempotency and recovery.

## Authority rules

1. Agent OS never authorizes consequential execution.
2. Agent OS never validates an approval as sufficient authority.
3. Agent OS never writes authoritative Platform evidence.
4. Agent OS never receives raw secret authority through this contract.
5. Platform policy and authorization are re-evaluated at consequential execution boundaries.
6. Platform evidence and audit identifiers are opaque to Agent OS.
7. Session, task and workflow IDs do not become Platform authority identifiers.

## Security

HTTPS is mandatory except explicit loopback testing. Redirects and embedded endpoint credentials are rejected. Remote response size, JSON shape and API version are bounded and validated. Model output, retrieved content, tool output, extension data and peer-agent messages are untrusted.

## Production seams

A production OS deployment requires a real authenticated Platform gateway, short-lived scoped credentials, certificate validation, durable Platform infrastructure, centralized evidence/audit, secret management, telemetry, fleet/control-plane services and operating-system service management.

## Reference guidance

The boundary follows current NIST agent identity/authorization work, OWASP 2026 agent-security guidance and the 2026-07-28 MCP security/authorization direction. These sources inform the design; repository contracts and tests remain implementation authority.