# Agent Catalog v3 — Phase 29: External Corpus Ingestion

Phase 29 extends the already-merged Phase 23 A2A discovery layer rather than duplicating it. The existing A2A 1.0 normalizer remains the standards-aware external-agent boundary; this phase adds a bounded generic curated-catalog adapter that feeds the Phase 28 candidate lifecycle.

## Pipeline

External source → normalized descriptive manifest → TaxonomyCandidate → Phase 28 normalization/deduplication/validation → review → canonical publication.

## Hard controls

- External records are untrusted descriptive metadata.
- Source provenance is mandatory and preserved into the candidate.
- Generic fields have bounded string and item counts.
- Capabilities are mandatory.
- No endpoint is invoked by the adapter.
- No credentials or permissions are imported.
- No Directory deployment or Registry release is created.
- No Platform authority is granted.

## Standards reconciliation

A2A Agent Cards remain handled by the existing standards-aware normalizer and its A2A 1.0 supportedInterfaces validation. This phase does not create a competing A2A parser.

NIST's current agent-tool taxonomy work recommends multidimensional classification across functionality, access patterns, risk, reliability, modality, monitoring and autonomy. A2A defines Agent Cards as discovery manifests containing identity, capabilities, skills and security requirements. These are discovery inputs, not execution authority.

## Gate

Phase 29 may merge only after full PR CI is green. After merge, merged-main CI must be green and a post-merge forensic audit must confirm that the extension composes with the existing Phase 23 A2A boundary and Phase 28 candidate lifecycle before Phase 30 begins.
