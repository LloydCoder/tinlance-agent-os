# M21 — Agent OS Observability

**Status: Complete.**

M21 provides OpenTelemetry-based lifecycle telemetry with correlation across tenant, subject, session, task, workflow and Platform run identifiers.

Boundary: OS telemetry is not authoritative execution evidence. Platform evidence remains authoritative.

Acceptance:
- traces/metrics are emitted through the OS observability layer;
- W3C context propagation is validated;
- sensitive prompts, credentials and confidential memory are not emitted by default;
- lifecycle telemetry remains distinct from Platform evidence.
