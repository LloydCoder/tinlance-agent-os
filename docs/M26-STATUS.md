# M26 Agent Directory & Desired-State Management

## Purpose

M26 adds a declarative desired-state layer above the existing M12 Agent Runtime.

- M12 Agent Runtime owns observed lifecycle state.
- M26 Agent Directory owns desired deployment intent.
- Reconciliation produces a deterministic, read-only plan.
- Agent Platform remains authoritative for identity, authorization, policy, approvals, budgets, consequential execution and evidence.

## Delivered

- durable desired agent definitions;
- generation-based compare-and-swap updates;
- compatibility metadata;
- rollout-channel metadata;
- desired lifecycle state;
- observed-state projection from M12;
- deterministic start/pause/stop/upgrade/reconfigure/block/no-op planning;
- workspace identity checks;
- public exports;
- acceptance tests;
- README, architecture and roadmap reconciliation.

## Security invariants

1. Desired state is metadata, not authorization.
2. A capability declaration is not a capability grant.
3. Missing observations produce BLOCKED, not implicit installation or execution.
4. Cross-workspace observations are rejected.
5. Reconciliation does not execute changes.
6. Generation conflicts fail closed rather than silently overwriting newer intent.

## Acceptance

The M26 test suite verifies durable desired state, compare-and-swap generation handling, lifecycle drift detection, version drift detection, and the absence of an authority path from directory metadata.
