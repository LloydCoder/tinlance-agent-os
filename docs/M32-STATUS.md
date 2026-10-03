# M32 — Resource, Cost & Capacity Runtime

**Status: Complete.**

M32 provides a durable usage ledger for OS-observed resource and cost attribution by workspace, agent, task and workflow.

Boundary: the ledger observes and reports. Platform budgets, quotas and authorization remain authoritative.

Acceptance:
- units and integer micro-costs are explicit;
- usage attribution is durable;
- capacity observations are inspectable;
- no local ledger can grant additional Platform budget.
