# Agent Catalog v3 — Phase 27: Evaluation-Aware Retrieval

Phase 27 adds deterministic retrieval over active CapabilityProfile records with explicit semantic, assurance, and operational gates.

## Contract

Retrieval separates:

- **semantic fit** — all requested capabilities and, when supplied, all requested skills;
- **evaluation evidence** — minimum evaluation score;
- **trust evidence** — minimum trust score;
- **operational constraints** — optional cost and latency ceilings;
- **lifecycle** — inactive/deprecated profiles are excluded;
- **ranking** — deterministic weighted score with stable profile-ID tie breaking.

Required capabilities and skills are hard requirements. Partial matches are not returned.

## Validation

`RetrievalRequirement` fails closed for:

- no required capabilities;
- evaluation/trust thresholds outside `[0, 1]`;
- negative cost ceilings;
- negative latency ceilings.

The retrieval limit must be positive.

## Evaluation basis

NIST's current TEVV guidance emphasizes documented measurement, repeatability, context-specific evaluation, and evidence-based assessment. Phase 27 therefore makes evaluation and trust explicit retrieval inputs rather than hidden model intuition.

## Security and authority boundary

Retrieval is descriptive only. It does **not**:

- authorize an agent;
- approve an action;
- grant permissions;
- create delegation;
- select tools for execution;
- bypass policy;
- admit an agent to the Platform;
- execute work.

Agent Platform remains the sole consequential authority plane.

External A2A metadata and MCP-derived metadata remain untrusted/descriptive inputs and must pass the governed taxonomy/profile lifecycle before they can influence production decisions.

## Determinism

Given the same profile set and requirement, retrieval produces the same result ordering. Score ties are resolved by stable profile ID.

## Gate

Phase 27 is complete only after:

1. full PR CI is green;
2. the PR is merged;
3. merged-main CI is green;
4. a post-merge forensic audit confirms the contract and authority boundaries;
5. only then may Phase 28 begin.
