# M1 — Agent Platform Adapter — COMPLETE

M1 provides the production-oriented integration boundary between Agent OS and the governed Tinlance Agent Platform.

## Implemented
- immutable tenant/subject/trace request context;
- per-operation request IDs;
- bearer-token provider boundary;
- HTTPS-by-default HTTP transport;
- explicit loopback-only HTTP exception for tests;
- redirect rejection and endpoint credential rejection;
- bounded JSON response parsing;
- API-version compatibility checks;
- fail-closed authentication and authorization errors;
- bounded retries for explicitly idempotent operations only;
- lifecycle operations for run creation/cancellation;
- agent discovery and capability references;
- approval-reference requests;
- Platform event and evidence reference retrieval;
- health/readiness integration;
- strict response-shape validation;
- provider-neutral transport protocol;
- adapter contract tests and transport integration tests;
- architecture tests preventing Platform implementation imports.

## Authority invariant
The adapter never authorizes an action, evaluates policy, validates approval authority, executes a tool, or creates evidence. It transports requests to and references results from Agent Platform. Agent Platform remains the sole authority and governed execution boundary.

## Compatibility
The adapter targets Agent Platform API version 1.1, matching the Platform's canonical lifecycle contract. The wire envelope and operation mapping are documented in docs/adr/0004-platform-adapter-wire-contract.md.

## Residual deployment responsibility
A production deployment must provide a real Platform HTTP/RPC gateway, scoped short-lived credentials, certificate validation, telemetry, secret management and durable Platform infrastructure. Those are deployment concerns and are not duplicated inside Agent OS.