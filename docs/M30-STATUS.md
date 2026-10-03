# M30 — Context & Knowledge Fabric

## Status

**Complete:** durable knowledge sources/documents/chunks, provenance-aware retrieval, authority/freshness scoring, classification/trust filtering, deterministic context budgets, tests and architecture/security documentation.

## Boundary

M30 extends M15 trusted memory. Memory answers **what the OS has retained**; the knowledge fabric answers **what external or application sources can contribute as context**.

Knowledge is data, never authority. Retrieval cannot grant capabilities, approvals, permissions or execution rights.

## Retrieval model

```text
Source -> Document -> Chunk -> Retrieval
                         |
                         +-> provenance
                         +-> freshness
                         +-> authority
                         +-> classification
                         +-> trust
                         |
                         v
                    Context Budget
                         |
                         v
                    Agent / Workflow
```

The current repository implementation provides deterministic lexical retrieval with explicit source authority and freshness scoring. A future vector/semantic backend can implement the same retrieval contract without moving retrieval authority into the OS.

## Security

- workspace-bound sources and documents;
- SHA-256 content digests;
- source version and collection timestamps;
- valid-from/valid-until metadata;
- classification filtering;
- quarantined content excluded from active ingestion;
- optional exclusion of untrusted content;
- provenance returned with every hit;
- deterministic context-size limits;
- no retrieval result is treated as an instruction or authorization.

## Research alignment

NIST's 2026 agent identity/authorization work emphasizes identification, least privilege, auditing/non-repudiation and controls for direct/indirect prompt injection. M30 therefore keeps knowledge provenance and trust separate from authority. citeturn6search4turn6search36


CI refresh: strict typed context assembly is included for all supported Python versions.
