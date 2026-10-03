# M27 Enterprise Workspace & Organization Fabric

## Delivered

- durable organization, project and environment hierarchy;
- development/staging/production environment semantics;
- workspace-to-hierarchy binding;
- layered configuration inheritance;
- workspace templates;
- active/archived lifecycle;
- generation-protected workspace updates;
- deterministic workspace export;
- cross-hierarchy integrity checks;
- public SDK/package exports;
- acceptance tests;
- README, architecture and roadmap reconciliation.

## Security invariants

1. The fabric is OS context, not authorization.
2. Cross-organization/project/environment bindings fail closed.
3. Workspace generation conflicts fail closed.
4. Configuration inheritance is deterministic.
5. Templates are metadata and cannot grant capabilities or execute code.
6. Agent Platform remains authoritative for identity, tenancy authorization, policy, approvals, budgets, execution and evidence.

## External alignment

The layered configuration model follows the same baseline/overlay separation used in current OpenTelemetry deployment guidance: platform-owned defaults can be overlaid by environment and workload-specific configuration without creating unmanaged one-off deployments. citeturn0search0

NIST's current AI/cybersecurity work continues to emphasize protected identity assertions and explicit access permissions while preserving separation of authorization responsibilities. citeturn0search14turn0search13
