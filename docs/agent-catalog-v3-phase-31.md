# Agent Catalog v3 — Phase 31: Security & Trust Classification

Phase 31 adds a deterministic, descriptive security/trust classification layer.

## Dimensions

Each classification records risk class, autonomy class, data sensitivity, write capability, network access, credential requirement, destructive-action potential, human-approval requirement, evidence requirement, and isolation requirement.

NIST's agent-tool taxonomy work identifies functionality, access patterns, risk, reliability, modality, monitoring, and autonomy as complementary dimensions rather than a single universal taxonomy. https://www.nist.gov/news-events/news/2025/08/lessons-learned-consortium-tool-use-agent-systems

A2A Agent Cards expose identity, capabilities, skills, interfaces, and security requirements for discovery. Catalog trust classification treats this information as descriptive metadata; it never turns an external declaration into Tinlance execution authority. https://a2a-protocol.org/dev/specification/agent-card/

## Fail-closed invariants

- destructive-action potential requires human-approval metadata;
- high/critical risk requires isolation metadata;
- autonomous classification requires evidence;
- credential requirements require network-access metadata;
- restricted data cannot be classified as low risk;
- low-risk classification cannot coexist with destructive action potential.

The classification fingerprint is deterministic.

## Authority boundary

SecurityTrustProfile is not authorization. It does not grant tools, credentials, approvals, execution, admission, delegation, Directory state, or Registry publication.

The Tinlance Platform remains authoritative for identity, authorization, approvals, runtime admission, budgets, sandboxing, evidence, audit, and delegation.

A2A 1.0 likewise requires implementations to enforce authorization boundaries on protocol operations; discovery metadata must therefore remain separate from authorization decisions.

OpenSSF Scorecard treats token permissions, pinned dependencies, branch protection, dangerous workflows, and code review as independent supply-chain controls. Taxonomy trust metadata is not a substitute for those controls. https://www.scorecard.dev/

## Gate

Phase 31 may merge only after exact-head CI is green. After merge, merged-main verification and a forensic audit must pass before Phase 32 begins.
