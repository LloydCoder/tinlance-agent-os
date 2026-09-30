# M12 Agent Lifecycle Runtime — Completion Record

**Status: COMPLETE**

M12 is the first executable agent lifecycle kernel above the M0-M11 Agent OS foundation.

## Implemented

- AgentDefinition with workspace, identity, version, entrypoint, declared capabilities, configuration, restart policy and runtime configuration.
- AgentRuntime with register, validate, start, run, pause, resume, stop and recover operations.
- Explicit lifecycle transition graph with fail-closed invalid transitions.
- Durable agents state in SQLite.
- Durable per-agent lifecycle event ledger.
- Monotonic per-agent event sequencing.
- Deterministic SHA-256 lifecycle event IDs.
- Optimistic concurrency using durable state versions.
- Durable heartbeat timestamps and expiry leases.
- Background heartbeat loop while running.
- Process-restart orphan detection through recover_orphans.
- Bounded restart policy and durable restart counters.
- Restart exhaustion transitions to FAILED.
- Immutable agent version binding for a durable agent identity.
- Reopened runtimes recover the durable definition and lifecycle state.
- Tests covering the complete lifecycle, persistence, deterministic events, version binding, invalid transitions, crashes, restart recovery, restart exhaustion, heartbeat leases and orphan recovery.

## Authority boundary

M12 does not authorize capabilities, approve actions, execute tools, issue secrets, enforce budgets, provide sandbox authority, or create authoritative evidence. Those remain Tinlance Agent Platform responsibilities.

## Acceptance result

    register -> validate -> start -> run -> pause -> resume -> stop

    crash / expired heartbeat -> CRASHED -> recover -> STARTING -> RUNNING

State transitions and their lifecycle events are committed atomically.

## Verification

The repository CI gates remain the acceptance authority. M12 is not considered complete until lint, formatting, mypy, Python 3.12/3.13/3.14 tests, coverage, dependency audit and architecture tests pass on the pull request.
