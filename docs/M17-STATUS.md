# M17 — Multi-Agent Runtime

## Status

**COMPLETE**

M17 adds the coordination layer for supervisor/child-agent runtimes while preserving the Tinlance Agent Platform as the sole authority plane.

## Implemented

- authenticated agent principals;
- durable supervisor and child task ownership;
- parent/child task hierarchy;
- same-tenant and same-workspace enforcement;
- delegation capability-subset verification;
- signed agent message envelopes;
- payload digest verification;
- anti-spoofing sender/recipient checks;
- monotonic per-task message sequencing;
- trace continuity across delegation;
- supervisor-scoped result aggregation;
- cancellation-tree propagation;
- durable coordination state;
- architecture and acceptance tests.

## Security boundary

The runtime never treats:

- an agent declaration as authorization;
- a delegated capability reference as a grant;
- a signed message as permission to execute;
- child-agent output as trusted authority.

The Agent Platform remains authoritative for identity, tenancy, capabilities, authorization, policy, approvals, execution and evidence.

## Failure model

Coordination state is durable. A child task remains linked to its supervisor and trace after process restart. Message sequence allocation is serialized in the local store. A forged or tampered message fails closed before delivery.

## Production seam

The repository's HMAC authenticator is a deterministic local implementation for tests. Production deployments should bind the same MessageAuthenticator and IdentityAuthenticator contracts to Platform-backed identity/key infrastructure.
