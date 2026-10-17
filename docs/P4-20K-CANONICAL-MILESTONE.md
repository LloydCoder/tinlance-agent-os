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

## Semantic identity normalization

Semantic uniqueness is computed from the normalized domain plus the set of normalized capabilities and skills. Tokens use Unicode NFKC normalization, whitespace collapsing, and case-folding; duplicate capability/skill tokens are collapsed before comparison. The key is encoded as deterministic structured JSON, not delimiter concatenation, so delimiter-bearing labels cannot collide.

The release gate and forensic auditor must use the same semantic-key function. Regression tests cover duplicate-token inflation, case/whitespace normalization, and delimiter-collision attempts. Display names and descriptions are never semantic identity.

## Evidence boundary

Generated fixtures exercise the release gate at scale; they are not represented as a real-world reviewed 20,000-entry catalog. A release claim requires an explicit persisted canonical inventory and independently verifiable provenance/review evidence for each entry.

## Non-inflation rule

Canonical count must not be multiplied by provider, model, geography, tool, protocol, locale, deployment mode, pricing tier, latency tier, customer, or language variants. Those are typed metadata/constraints, not independent semantic archetypes.

## Continuous taxonomy

After the 20K milestone, canonical inventory is continuously extensible subject to semantic uniqueness, provenance, review, ontology governance, deprecation and migration evidence.

The historical 420 seed remains a seed, not a permanent deployment count and not a taxonomy ceiling.

## Authority boundary

Catalog metadata can improve discovery and matching but can never grant execution authority. Agent Platform remains authoritative for identity, authorization, policy, approvals, budgets, sandboxing, execution, evidence and audit.
