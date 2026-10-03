# M40 — Agent OS Intelligence & Adaptive Runtime

## Status

**Complete** — durable adaptive policies, observations, explainable recommendations and generation-protected decisions are implemented with tests and reconciled documentation.

## Boundary

M40 is an optimization/intelligence layer above the OS lifecycle runtimes. It does not become an authorization, approval, budget, execution or evidence authority. Accepted recommendations are still intents that must pass through the owning runtime and Agent Platform.

## Acceptance

- policy/objective/metric/target/tolerance are explicit;
- observations are workspace scoped and unit/sample-size validated;
- recommendations are explainable from stored observations;
- cross-workspace use fails closed;
- recommendation decisions use generation checks;
- adaptive records remain durable and inspectable;
- no Platform authority is duplicated.
