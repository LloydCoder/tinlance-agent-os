# ADR-0004: Versioned Agent Platform Adapter Contract

## Decision
Agent OS integrates with Agent Platform through a provider-neutral transport and a versioned request/response envelope. The concrete HTTP transport is an adapter; it does not contain authorization, policy, approval, budget or execution logic.

The HTTP request body is the canonical Platform APIRequest shape. The adapter also requires X-Tinlance-API-Version: 1.1 and a fresh X-Request-ID: tenant identifier, authenticated subject identifier, operation name and operation payload. API version and correlation metadata are carried in headers so the body remains compatible with the Platform API contract.
The bearer credential is transported only in the HTTP Authorization header and is never placed in the operation payload. The response body follows the Platform APIResponse shape; the negotiated API version is carried in the X-Tinlance-API-Version response header.

## Operations

The M1 adapter maps the OS client contract to these stable operation names:
- principal.get
- agents.list
- runs.create
- runs.cancel
- capabilities.list
- approvals.request
- runs.events
- runs.evidence
- health

The Platform remains authoritative for the meaning and authorization of each operation.

## Reliability

Only operations explicitly classified as idempotent may be retried automatically. Run creation, cancellation and approval requests are never retried automatically. This avoids duplicate side effects when a connection fails after the Platform has already applied a request.

## Security

HTTPS is mandatory except for explicitly enabled loopback test endpoints. Redirects are rejected so credentials cannot be forwarded to an unexpected origin. Embedded endpoint credentials are rejected. Response sizes and JSON structure are bounded and validated. API-version mismatches fail closed.

## Consequence

The OS can change transport implementation without changing its domain contract, while the Platform retains a single authority plane.

## Request identity

Every request carries a fresh X-Request-ID. The same identifier is also sent as Idempotency-Key so the Platform gateway can deduplicate a consequential request when its semantics permit. Agent OS still never automatically retries non-idempotent operations; the key is a server-side safety aid, not a license to repeat side effects.
