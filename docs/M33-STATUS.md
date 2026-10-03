# M33 — Evaluation & Agent Quality Runtime

## Status

**Complete** — repository-owned evaluation contracts, durable persistence, deterministic gates, comparison semantics, tests and documentation are implemented.

## Scope

M33 gives Agent OS a stable evaluation lifecycle without making evaluation an authority plane.

- **Cases:** versioned suite/case identities with input and expected-output digests.
- **Runs:** durable workspace/agent/workflow/model attribution and lifecycle state.
- **Measurements:** integer values, explicit units, timestamps and optional evidence references.
- **Gates:** minimum/maximum threshold rules evaluated deterministically and fail closed on missing or mismatched units.
- **Comparisons:** baseline/candidate metric deltas for regression analysis.

## Boundary

Evaluation observes and assesses Agent OS workloads. It does not execute consequential work, grant capabilities, authorize actions, enforce budgets/quotas, or create authoritative Platform evidence.

FAS/FAS-Bench and future benchmark providers remain external integrations. They can publish measurements through the evaluation contracts without becoming kernel dependencies.

## Acceptance evidence

- durable case/run/measurement/gate state is SQLite-backed;
- duplicate measurement identities are rejected;
- naive timestamps are rejected;
- gate evaluation requires an observed metric and exact unit match;
- baseline/candidate comparison is deterministic;
- architecture CI verifies the module does not introduce a second authority plane.

## Next milestone

M34 — Enterprise Fleet & Remote Control Plane.
