# Tinlance Agentic OS Roadmap

All milestones M0-M11 are implemented on the current development line.

| Milestone | Scope | Status |
|---|---|---|
| M0 | Architecture Foundation | COMPLETE |
| M1 | Agent Platform Adapter | COMPLETE |
| M2 | Local Agent OS Daemon | COMPLETE |
| M3 | Workspace + Sessions + Tasks | COMPLETE |
| M4 | Workflow Engine | COMPLETE |
| M5 | Context + Memory | COMPLETE |
| M6 | Agent Application Model | COMPLETE |
| M7 | System Integration | COMPLETE |
| M8 | Desktop/Shell | COMPLETE |
| M9 | Extensions | COMPLETE |
| M10 | Enterprise / Remote OS | COMPLETE |
| M11 | Production / Distribution | COMPLETE |

## Architectural rule
Agent OS owns lifecycle, composition, workspace/session/task state, workflows, applications,
presentation and system abstraction. Tinlance Agent Platform remains the sole authority for
identity, tenancy authorization, policy, approvals, budgets, governed execution and authoritative evidence.

## M2-M11
M2 provides a bounded same-user Unix-domain local control daemon. M3 provides durable SQLite
workspace/session/task/event state. M4 provides cycle-checked dependency workflows. M5 provides
scoped classified memory with restricted data failing closed. M6 provides declarative application
manifests and lifecycle. M7 provides filesystem/process/notification abstractions. M8 provides a
toolkit-neutral shell model. M9 provides capability-scoped extensions. M10 provides secure remote
agent/fleet integration seams. M11 provides content-addressed release verification and staged
apply/rollback.

## Verification
CI must retain unit, contract and architecture coverage, Python 3.12-3.14, Ruff, format, mypy,
coverage and dependency auditing. No milestone may duplicate Platform authorization, approval,
policy, sandbox, model or evidence authority.
