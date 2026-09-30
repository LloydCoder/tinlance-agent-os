# M15 Context + Trusted Memory — Completion Record

## Scope

M15 replaces the original six-column memory primitive with a durable security-aware memory subsystem and context assembler.

## Implemented

- working, session, task, agent and workspace long-term memory scopes;
- durable SQLite persistence across process/session boundaries;
- provenance with source type, source ID, actor, origin, collection time and parent digest;
- SHA-256 integrity digests over memory identity, content, version and provenance;
- public/internal/confidential/restricted classification;
- trusted-instruction, verified-fact, untrusted-content and quarantined trust classes;
- scope- and workspace-aware retrieval;
- classification ceilings that fail closed;
- default retention by memory scope plus explicit TTL/expiry;
- explicit tombstone deletion;
- immutable version history with compare-and-swap updates;
- stale-write conflict rejection;
- deterministic poisoning detection for common persistent prompt-injection, exfiltration, security-bypass and credential/key patterns;
- quarantine and explicit quarantine inspection;
- deterministic keyword retrieval;
- trust-separated context assembly;
- SDK remember, recall and context-assembly helpers.

## Backward compatibility

The historical M0-M11 MemoryStore call shape remains available as a compatibility façade, with restricted legacy writes still fail closed. New calls use the typed M15 contracts and security boundary.

## Security boundary

Memory is not an authority channel. A memory record cannot create a Platform capability, approval, run, secret, evidence reference or policy decision.

Classification and trust are separate controls. Classification determines whether a caller may retrieve the data. Trust determines how retrieved data is categorized for downstream context construction.

Suspicious content is quarantined before it becomes active memory. Quarantine is fail-closed for ordinary retrieval. The detector is intentionally deterministic and is not treated as a semantic truth oracle.

## Persistence acceptance

The M15 test suite verifies that a record written through one StateStore instance can be reopened and retrieved through another instance while preserving provenance, version and integrity metadata.

## Adversarial acceptance

Tests cover:

- cross-workspace access;
- cross-agent access;
- cross-session access;
- cross-task access;
- confidential/restricted retrieval ceilings;
- stale-version update races;
- poisoning/quarantine;
- trust-channel separation;
- retention/expiry;
- deletion;
- invalid scope contracts.

## Research alignment

OWASP's 2026 Agentic Applications guidance identifies ASI06 Memory & Context Poisoning as a persistent attack surface affecting stored context, summaries, embeddings and RAG stores. Current OWASP material also recommends source attribution, scoped access, retention limits, anomaly detection and rollback-oriented controls. M15 implements the local storage, provenance, isolation, retention, quarantine and context-separation portions appropriate to this repository; external truth validation and enterprise policy remain higher-layer concerns.

NIST's 2026 AI Agent Standards Initiative emphasizes secure agent operation, interoperability, identity and authorization. M15 preserves the same separation: memory can influence agent context but never becomes authorization.

## References

- OWASP Top 10 for Agentic Applications 2026 — ASI06 Memory & Context Poisoning
- OWASP Memory Is a Feature. It Is Also an Attack Surface (May 13, 2026)
- OWASP Threats and Mitigations 1.1 — memory access, provenance, retention and poisoning controls
- NIST AI Agent Standards Initiative (2026)
