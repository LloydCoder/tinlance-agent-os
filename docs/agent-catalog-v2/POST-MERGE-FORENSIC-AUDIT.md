# Agent Catalog v2 — Post-Merge Forensic Audit

Audit date: 2026-10-05

## Scope

This audit revalidated the merged Catalog v2 phases 0-17 against the live implementation, CI history, the Agent OS M17/M26/M36 contracts, Agent Platform authority boundaries, and current external interoperability/security standards.

## Findings

### CI gate integrity

Phases 0-5 had green CI at their merge heads.

Phases 6-17 were merged despite red or cancelled historical PR runs. This was a process-integrity defect, not evidence that the implementation was correct. A root-cause remediation was applied after merge and required a fresh green matrix before any further phase could proceed.

The remediation PR is itself gated by:
- Python 3.12
- Python 3.13
- Python 3.14
- Architecture boundary
- Ruff lint/format
- mypy
- test suite and >=85% coverage
- dependency audit

### Phase 5 profile contract

The profile contract previously lacked explicit operational quality and supply-chain signals. It now records evaluation score, trust score, cost, latency, artifact digest, signature reference and SBOM reference while remaining authority-neutral.

### Phase 6 catalog storage

The original store was in-process despite the phase documentation using durable-storage language. A SQLite-backed durable adapter now persists versioned profile records atomically and reloads them on startup. The in-process index remains useful for deterministic discovery.

### Phases 8-10 discovery/matching/selection

The original implementation matched only exact capability/tool/environment/protocol constraints. It now exposes evaluation, trust, cost and latency constraints. Selection remains deterministic and still does not authorize execution.

### Phases 11-13 team formation

Team budgets now reject impossible active-agent limits. Team planning preserves the original user goal into TeamSpec. Team graph execution remains an adapter to M17 rather than a second runtime.

### Phase 14 delegation

Delegation remains proposal-only and authority-neutral. Platform admission remains the source of effective authority.

### Phase 15 handoff/synthesis

Handoff remains evidence-first. Synthesis is descriptive output and does not create verdict authority.

### Phase 16 interoperability

A2A and MCP remain metadata/protocol adapters rather than authority mechanisms. Current A2A Agent Cards contain identity, supported interfaces, capabilities, security requirements and skills; signed cards can provide integrity. Current MCP 2026-07-28 is stateless at protocol level, adds server discovery and authorization hardening, and places Tasks in an extension. Catalog metadata therefore needs explicit protocol-version, provenance and trust semantics.

### Phase 17 evaluation

Evaluation remains a quality signal and regression mechanism. It cannot grant capability or authorize execution.

## External security reconciliation

Current NIST agent standards work emphasizes interoperability, identity, authentication and security. Current OWASP agentic guidance highlights identity/privilege abuse, insecure inter-agent communication, cascading failures, supply-chain compromise, memory/context poisoning and rogue agents.

Catalog v2 therefore treats trust, provenance, protocol compatibility, evaluation, operational limits and evidence references as semantic constraints. Platform remains authoritative for identity, authorization, policy, approval, budgets and governed execution.

## Remaining Phase 18+ requirements

The following are intentionally not claimed complete by this audit:

1. adversarial Catalog/team security suite;
2. recursive-spawn and budget-storm tests;
3. malicious/forged Agent Card and package tests;
4. inter-tenant isolation tests for Catalog/team planning;
5. production crash-recovery and idempotency validation;
6. complete A2A/MCP conformance adapters;
7. final GA documentation and release certification.

## Gate

No Phase 18 implementation begins until this remediation branch is fully green and merged, followed by a post-merge main CI verification.
