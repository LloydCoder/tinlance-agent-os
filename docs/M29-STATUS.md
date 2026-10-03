# M29 — Scheduler & Job Runtime

## Status

**Complete:** repository-owned scheduler contracts, durable persistence, deterministic cadence, leasing, concurrency controls, misfire handling, recovery, tests and documentation.

## Scope

M29 adds the temporal execution-control layer above the M28 event runtime and M16 workflow runtime:

```text
Cron / interval / one-shot / calendar
                |
                v
           Scheduler
                |
                v
              Job
                |
                v
             Task
                |
                v
      Workflow / Agent runtime
                |
                v
        Agent Platform Run
```

The scheduler owns *when* OS work should become a job and the durable lifecycle of that job. It does not decide whether consequential work is authorized.

## Controls

- UTC-normalized persisted schedule timestamps;
- IANA timezone validation for local calendar/cron semantics;
- deterministic five-field cron parsing;
- interval, one-shot and calendar schedules;
- generation-protected schedule updates;
- explicit skip/run-once/catch-up misfire policies;
- deterministic job IDs derived from schedule ID + scheduled occurrence;
- durable queued/running/terminal job state;
- worker leases with expiry and recovery;
- per-schedule maximum concurrency;
- bounded due-job queries;
- dispatcher failures become durable job failures rather than disappearing work;
- scheduler metadata is data and cannot mint Platform authority.

## Acceptance

The M29 test suite verifies:

1. interval schedules produce deterministic jobs;
2. catch-up preserves missed interval occurrences;
3. cron schedules honor IANA timezones;
4. maximum concurrency prevents conflicting leases;
5. expired worker leases are recoverable;
6. stale schedule generations are rejected;
7. dispatcher failures are persisted as terminal failures.

## Boundary

M29 does not execute customer code, authorize tools, mint capabilities, approve actions, or produce authoritative evidence. A dispatched job must enter the existing Agent OS Task/Workflow path and consequential work must still enter Agent Platform governed execution.

## CI verification

The M29 acceptance suite is verified through the repository quality and architecture gates across Python 3.12, 3.13 and 3.14 before the milestone is merged.

## Operational note

The local SQLite scheduler is the single-node durable mode. CI gate replay is required after any scheduler implementation change. Distributed scheduling, leader election, multi-node queues and regional failover remain M38 infrastructure work; M29 deliberately exposes the lease and persistence contracts needed to replace the local store without changing scheduler semantics.
