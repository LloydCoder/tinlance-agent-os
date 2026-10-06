# Agent Catalog v3 — Phase 24: Semantic Deduplication

Phase 24 adds deterministic semantic reconciliation so catalog growth does not become duplicate inflation.

## Design

The deduplicator compares domain, canonical capability set, skill set, normalized name, and deterministic semantic digest.

It emits:

- equivalent — safe for deterministic equivalence classification;
- specialized — one semantic scope is a subset of another;
- generalized — inverse of specialized;
- related-but-distinct — materially different boundary or domain;
- review-required — similarity is high enough to warrant human review, but not safe for automatic merging.

Only deterministic structural relations are marked automatic. Lexical similarity never authorizes a merge. Review-required matches are explicitly prevented from being automatic.

The engine produces pairwise comparison reports. It does not mutate canonical records, delete candidates, or publish taxonomy entries.

## Anti-inflation policy

A domain, model, provider, geography, tool, protocol, deployment environment, customer, cost tier, latency tier, or permission level is not independently sufficient to create a new canonical archetype. Such distinctions belong in capability/profile/constraint layers unless the semantic work boundary itself changes.

## Authority boundary

Phase 24 is descriptive reconciliation only. It does not grant authorization, execute tools, issue approvals, access secrets, control sandboxing, or replace Agent Platform R10, M17 coordination, M26 Directory, or M36 Registry.

## Gate

Phase 24 is complete only after unit tests, architecture tests, full CI across supported Python versions, dependency/security checks, merged-main CI, and a post-merge forensic audit are green.
