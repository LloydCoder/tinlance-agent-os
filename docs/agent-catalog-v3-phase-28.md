# Agent Catalog v3 — Phase 28: Candidate Pipeline

Phase 28 establishes the controlled lifecycle for external and generated taxonomy candidates.

## Lifecycle

`DISCOVERED → NORMALIZED → CLUSTERED → CANDIDATE → VALIDATED → REVIEWED → CANONICAL`

Deprecated entries leave the canonical set through `CANONICAL → DEPRECATED`.

This module implements the structural portion of the lifecycle. Clustering, human review, and canonical publication remain separate gates.

## Hard controls

Every candidate requires non-empty identity and domain, at least one capability, explicit provenance/source references, deterministic normalization, a SHA-256 semantic fingerprint, structural validation before review, an explicit review transition, and a stable canonical identifier before canonical state.

Capability and skill collections, when present, must contain non-blank values. Provenance must contain only non-blank references; malformed provenance is rejected at the candidate trust boundary rather than silently discarded.

A candidate cannot jump directly from discovery to canonical publication.

## Deduplication

Deduplication uses normalized domain, name, description, capabilities and skills. The representative is deterministic and prefers the candidate with the larger provenance set; fingerprint ordering breaks remaining ties.

This is intentionally conservative: semantic equivalence beyond normalized identity is a future clustering/evaluation concern, not an assumption hidden inside string matching.

## Security boundary

Candidate data is untrusted descriptive metadata. It does not grant authority, select tools, authorize actions, create delegation, change Platform policy, execute code, or admit an agent to the runtime.

## Research alignment

NIST identifies functionality, access patterns, risk, reliability, modality, monitoring and autonomy as complementary dimensions and recommends multidimensional approaches rather than a single taxonomy axis. A2A's current Agent Card model likewise describes agent identity, capabilities, skills and security requirements for discovery; discovery metadata is not equivalent to execution authority.

## Post-merge forensic remediation

The merged Phase 28 implementation was re-audited before Phase 29 advancement. The audit identified and corrected a fail-open metadata condition in which a source-reference tuple containing blank values could pass the initial non-empty tuple check and then be silently filtered during normalization. The remediation also hardens blank capability/skill values and blank canonical identifiers.

## Gate

Phase 28 may merge only when full PR CI is green. After merge, main CI must be green and the merged state must pass a forensic audit before Phase 29 begins.
