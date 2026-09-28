# Agent OS Security Controls

This document is the implementation-level security companion to security/threat-model.md.

## Control objectives

| Area | Control | Enforcement |
|---|---|---|
| Authority | No local authorization kernel | Architecture tests + Platform adapter boundary |
| Identity | Tenant/subject propagated to Platform | Immutable request context |
| Transport | HTTPS by default | Endpoint validation |
| Redirects | No credential forwarding | Redirect handler rejects redirects |
| Protocol | Version and schema validation | Transport/adapter |
| Reliability | No blind retries of side effects | Explicit idempotent flag |
| Local IPC | Same-user peer enforcement | SO_PEERCRED where supported |
| IPC resource use | Bounded request size/time | Daemon config |
| Local state | Durable SQLite | WAL + synchronous FULL |
| Database integrity | Referential integrity | SQLite foreign keys |
| Memory | Workspace/scope isolation | Query predicates + classified storage |
| Sensitive memory | Fail closed | Confidential/restricted rejection |
| Filesystem | Root confinement | Resolved-path containment check |
| Process execution | Explicit allowlist | Fixed trusted executable directories |
| Process abuse | Timeout + process-group kill | Popen + start_new_session |
| Extensions | Capability-scoped context | Manifest/grant intersection |
| Remote endpoints | Secure scheme/no embedded credentials | URL validation |
| Updates | Size + SHA-256 verification | ReleaseArtifact |
| Update versioning | Staged version must match applied version | UpdateManager |
| CI supply chain | Immutable action references | SHA-pinned GitHub Actions |

## Agent-specific controls

Agent OS treats the following as untrusted:

- model-generated text;
- retrieved documents/web content;
- tool output;
- extension-provided data;
- remote Platform responses before schema validation;
- inter-agent messages.

No such content can independently authorize a consequential Platform action.

OWASP's current agent security guidance highlights excessive agency, memory poisoning, tool abuse, data exfiltration, approval manipulation, runaway cost/retry behavior, and supply-chain attacks as material agent risks.

## Approval model

Agent OS may request an approval through the Platform adapter, but it does not decide that an approval is valid.

High-impact actions should be bound by the Platform to the actor, tool/action, target, normalized parameters, time and expiry, with replay protection. This is intentionally outside the OS authority plane.

## Observability model

OS lifecycle occurrences should be represented as structured events. Duration-bearing work should be represented as spans. Correlation should include OS task/session/workflow identifiers and the Platform run identifier without copying sensitive payloads into telemetry by default.

## Supply-chain model

The repository verifies downloaded release bytes by size and SHA-256. Production distribution should additionally use signed artifacts and verifiable build provenance/attestations. SLSA defines provenance as verifiable information about where, when and how an artifact was produced.

## Residual deployment responsibilities

The following are intentionally deployment/provider responsibilities:

- enterprise IdP/SSO and short-lived credential issuance;
- certificate trust and rotation;
- centralized audit/evidence retention;
- telemetry collection and alerting;
- fleet control plane;
- artifact signing and provenance service;
- operating-system sandboxing/service management;
- hardware/TPM trust;
- desktop security controls.

The repository must not imply that these controls exist merely because an integration interface exists.
