# Agent Catalog v3 — Phase 27: Evaluation-Aware Retrieval

Phase 27 adds deterministic retrieval over capability profiles with explicit evaluation and trust gates.

## Design

Retrieval separates:

- semantic fit: capability and skill coverage;
- evaluation evidence: minimum evaluation score;
- trust evidence: minimum trust score;
- operational constraints: cost and latency ceilings;
- ranking: deterministic score with stable profile-ID tie break.

A retrieval result is descriptive. It is not admission, authorization, approval, delegation, tool access, or execution.

## Evaluation basis

NIST's current AI measurement work emphasizes documented, repeatable TEVV, context-specific measurement, and independent evaluation. Phase 27 therefore treats evaluation and trust as explicit retrieval inputs rather than hidden model intuition.

## Safety properties

- Missing required capabilities are excluded.
- Evaluation/trust thresholds are hard filters.
- Cost/latency limits are hard filters when requested.
- Ranking is deterministic and reproducible.
- Platform admission remains the final authority.
- No retrieval result grants permissions or bypasses policy.

## Gate

Phase 27 is complete only after full PR CI, merge, green merged-main CI, and forensic post-merge audit.
