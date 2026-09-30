# M16 — Real Workflow Runtime

## Status

**COMPLETE**

M16 upgrades the repository's deterministic workflow DAG into a durable runtime while preserving the Agent Platform authority boundary.

## Implemented

- sequential dependency execution;
- parallel execution of independently ready branches;
- deterministic conditions;
- bounded retries and exponential backoff;
- workflow deadlines;
- step timeout/deadline propagation;
- cancellation;
- Platform Run cancellation propagation;
- approval gates;
- human-input gates;
- compensation;
- per-step checkpoints;
- durable workflow/step/event state;
- process-crash recovery;
- resume;
- event triggers;
- persisted schedules and due-schedule firing;
- stable per-instance/per-step idempotency keys;
- Platform Run mapping;
- architecture and acceptance tests.

## Files

- `src/tinlance_agent_os/workflow.py` — validated workflow contracts and deterministic DAG semantics.
- `src/tinlance_agent_os/workflow_runtime.py` — durable execution/recovery runtime and Platform adapter.
- `src/tinlance_agent_os/store.py` — durable workflow instances, step runs, events and schedules.
- `tests/test_m16_workflow_runtime.py` — adversarial acceptance coverage.
- `docs/ARCHITECTURE.md` — authority, durability and recovery design.
- `docs/ROADMAP.md` — milestone status and acceptance definition.

## Consequential side-effect safety

The runtime does not claim exactly-once side effects. Instead it guarantees that a logical consequential step keeps the same idempotency key across attempts, retries and crash recovery. The Platform remains the authoritative execution/idempotency boundary.

This is the required property for the failure window:

```text
Platform side effect
       |
       X process crash
       |
local checkpoint not committed
```

Recovery retries the same logical operation with the same Platform idempotency key instead of inventing a new action.

## Security invariants

1. Workflow metadata cannot grant capabilities.
2. Approval gates do not create local authority.
3. Human input is data, not authorization.
4. Platform Runs remain authoritative for consequential execution.
5. Tenant/workspace identity is persisted with every workflow instance.
6. Cross-instance state is not reused.
7. Recovery retains stable step identity and idempotency.
8. Workflow conditions are deterministic and do not execute arbitrary code.
9. Cancellation propagates to known active Platform runs.
10. Failure compensation is explicit in the workflow definition.
