# Agent Catalog v3 — Phase 30: 10K Release Gate

Phase 30 establishes the deterministic release contract for a 10,000+ canonical-archetype inventory.

## Important non-inflation rule

The release gate does not generate agents and does not accept arbitrary domain/model/tool/locale combinations as new archetypes. A 10K release is valid only when a genuinely distinct, reviewed canonical inventory already exists.

The gate is therefore a proof boundary, not a synthetic taxonomy generator.

## Required invariants

- at least 10,000 canonical entries;
- every entry is in CANONICAL lifecycle state;
- every entry has a stable canonical identifier;
- canonical identifiers are unique;
- semantic archetype keys (domain + capabilities + skills) are unique independent of display name/description;
- 100% of entries retain provenance;
- at least 30 distinct domains are represented;
- deterministic SHA-256 inventory digest;
- no Platform authority, Directory deployment, Registry publication, or runtime execution is performed.

## Release manifest

The manifest records the release name, target count, actual canonical count, domain diversity, provenance coverage, semantic uniqueness, and deterministic inventory digest.

The digest is order-independent so the release artifact is reproducible. Display-name or prose changes cannot manufacture a distinct archetype when the governed semantic dimensions are unchanged.

## Security and architecture boundary

This module is descriptive release validation only. Platform remains the runtime authority. Directory and Registry semantics remain outside Catalog. Candidate ingestion remains governed by Phase 28, and external discovery remains governed by Phase 29.

## Post-merge forensic remediation

The merged Phase 30 gate was re-audited after release. A semantic deduplication weakness was found: the inherited candidate fingerprint included display name and description, so a renamed/reworded duplicate could evade the release gate. The remediation defines release identity from domain, capabilities and skills, with stable IDs and provenance retained separately for inventory integrity.

## Gate

Phase 30 may merge only with full CI green. After merge, main CI must be green and a forensic audit must verify that the release gate cannot be used to manufacture semantic entries or bypass canonical review.
