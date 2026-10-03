# M38 — Reliability, HA, DR & Chaos

## Status

**Complete** — reliability deployment profiles, worker leases, DR plans, chaos scenarios, readiness checks, tests and documentation are implemented.

## Boundary

M38 defines reliability contracts and readiness state. Production PostgreSQL, queues, leader election, fencing, backups, regional failover and chaos execution remain deployment infrastructure.

## Acceptance

- distributed profiles require multiple regions;
- worker leases are unique and generation protected;
- lease expiry is timezone-aware and future-dated;
- DR plans explicitly carry backup/restore targets and RPO/RTO;
- chaos scenarios explicitly carry blast radius;
- readiness is derived from durable state;
- no second authority plane is introduced.
