# Agent Catalog v3 — Phase 28: Candidate Pipeline

Phase 28 establishes a controlled lifecycle for external and generated taxonomy candidates.

## Lifecycle

`DISCOVERED → NORMALIZED → CLUSTERED → CANDIDATE → VALIDATED → REVIEWED → CANONICAL`

Deprecated entries leave the canonical set through `CANONICAL → DEPRECATED`.

Every transition is explicit and forward-only. The implementation rejects skipped, reversed, or fabricated lifecycle transitions, including direct construction of non-discovered states. Review state also requires a non-empty governance evidence reference, and canonical IDs are constrained to a stable lowercase identifier grammar.

## Hard controls

Every candidate requires:

- non-empty identity and domain;
- at least one capability;
- explicit provenance/source references;
- deterministic normalization;
- a SHA-256 semantic fingerprint;
- structural validation before review;
- explicit governance review state with a review evidence reference before canonical publication;
- a stable canonical identifier at publication.

Canonical publication is exposed only through `publish_canonical()` and requires `REVIEWED` state plus a stable canonical ID. The candidate module never executes work or grants authority.

## Deduplication

Initial deduplication operates only on normalized structural identity: domain, name, description, capabilities and skills. The representative is deterministic and prefers the larger provenance set; fingerprint ordering breaks remaining ties.

This is intentionally conservative. Deeper semantic equivalence, clustering quality, and cross-source ontology reconciliation belong to later phases and must not be hidden inside candidate ingestion.

## Security boundary

Candidate data is untrusted descriptive metadata. It does not grant authority, select tools, authorize actions, create delegation, change Platform policy, execute code, or admit an agent to the runtime.

## Research alignment

NIST's current [TEVV-Athlon framework](https://www.nist.gov/artificial-intelligence/ai-research/tevv-athlon-framework-evaluating-ai-systems) emphasizes context-specific, repeatable measurement and structured evidence for AI-system evaluation. NIST's [agentic evaluation probes](https://www.nist.gov/programs-projects/building-evaluation-probes-agentic-ai) emphasize machine-readable audit trails and evidence grounding. OWASP's [agentic security guidance](https://genai.owasp.org/llmrisk/llm062025-excessive-agency/) reinforces least functionality, least privilege, human approval for high-impact actions, and complete mediation. Candidate lifecycle controls therefore remain deterministic and governance-gated rather than LLM-authoritative.

A2A-style discovery metadata can inform candidate inputs, but discovery metadata is not execution authority. MCP metadata likewise remains descriptive input to governed ingestion.

## Phase boundary

Phase 28 owns candidate lifecycle and structural validation.

It does not own:

- external corpus ingestion (Phase 23);
- semantic deduplication/clustering quality (Phase 24);
- broad domain expansion (Phase 25);
- evaluation/retrieval ranking (Phase 27);
- security/trust classification (Phase 31);
- A2A/MCP interoperability mapping (Phase 32);
- Platform authorization or admission.

## Gate

Phase 28 may merge only when full PR CI is green. After merge, merged-main CI must be green/observable and a post-merge forensic audit must confirm the lifecycle, review-evidence gate, tests, docs, workflow integrity, and authority boundary before Phase 29 begins.


## CI release gate

No Phase 28 merge is valid without a completed GitHub Actions CI run for the exact PR head SHA, with every required job successful. A missing, pending, or unobservable workflow is a blocker, not an implicit pass.
