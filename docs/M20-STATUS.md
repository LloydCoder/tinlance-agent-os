# M20 — Local/Remote Agent Runtime

**Status: COMPLETE**

M20 adds supervised local and authenticated remote runtime primitives without creating a second authority plane.

Implemented:
- local process supervision with host resource limits;
- root-bound filesystem capability binding;
- explicit secure network endpoint policy;
- remote endpoint enrollment and fingerprint identity;
- workspace/tenant binding;
- heartbeat, reconnect, stale endpoint detection;
- draining and disconnect states;
- deterministic workspace fleet routing;
- durable remote task records;
- stable remote idempotency keys;
- remote task cancellation;
- Platform Run mapping;
- MCP transport adapter rather than a parallel remote wire protocol;
- adversarial tests for identity, workspace, network and authority boundaries.

The remote runtime is a worker plane. Agent Platform remains authoritative for identity, tenancy, capabilities, authorization, approvals, policy, consequential execution and evidence.

Research basis: current MCP documentation describes a stateless protocol direction and explicit extensions/handles for long-running work; M20 therefore keeps durable endpoint/task state in Agent OS while using MCP as the interoperability transport. citeturn1search10turn1search12
