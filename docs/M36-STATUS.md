# M36 — Agent Marketplace & Enterprise Registry

## Status

**Complete** — publisher, package and version contracts; supply-chain metadata; trust/quarantine lifecycle; tests and documentation are implemented.

## Boundary

The registry stores distribution metadata and lifecycle state. It does not execute artifacts, grant capabilities or authorize installation. External signing, artifact storage, vulnerability scanning and marketplace UI remain deployment integrations.

## Acceptance

- publisher/package/version state is durable;
- blocked publishers are rejected;
- published versions require signatures;
- artifacts require strict SHA-256 digests;
- provenance and SBOM references are explicit;
- version state transitions are generation protected;
- duplicate version identities are rejected.
