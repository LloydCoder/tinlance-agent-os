# P4 — 20K Canonical Catalog Milestone

The Agent Catalog v3 20K boundary is a **GA release milestone**, not a permanent maximum.

## Release proof

A 20K release requires:
- at least 20,000 canonical entries;
- unique canonical identifiers;
- semantic uniqueness;
- provenance for every entry;
- review evidence for every entry;
- at least 50 distinct domains;
- deterministic inventory digest.

## Non-inflation rule

Canonical count must not be multiplied by provider, model, geography, tool, protocol, locale, deployment mode, pricing tier, latency tier, customer, or language variants. Those are typed metadata/constraints, not independent semantic archetypes.

## Continuous taxonomy

After the 20K milestone, canonical inventory is continuously extensible subject to semantic uniqueness, provenance, review, ontology governance, deprecation and migration evidence.

The historical 420 seed remains a seed, not a permanent deployment count and not a taxonomy ceiling.

## Authority boundary

Catalog metadata can improve discovery and matching but can never grant execution authority. Agent Platform remains authoritative for identity, authorization, policy, approvals, budgets, sandboxing, execution, evidence and audit.


## Forensic boundary — gate implementation versus inventory release

The repository's 20K fixture is synthetic test data. It demonstrates that the release gate rejects a sub-target inventory, low domain diversity, non-canonical entries, missing provenance/review references, duplicate IDs, and duplicate semantic keys. It is **not** evidence that 20,000 genuine, ontology-reviewed archetypes have been curated or published.

The milestone's production-release claim must remain blocked until a separately versioned inventory artifact is supplied and its exact digest, source provenance, human review evidence, ontology references, semantic-deduplication report, and domain coverage are independently verified. A green unit test or synthetic fixture must never be promoted into a claim that the actual 20K inventory exists.

The release digest covers the canonical identifier, normalized name and description, normalized semantic dimensions, source references, review reference, and candidate state. Duplicate labels are normalized and deduplicated before semantic uniqueness checks, so repeating a capability or skill cannot manufacture a new archetype.
