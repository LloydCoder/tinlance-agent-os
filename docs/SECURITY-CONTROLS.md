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
| Reliability | Consequential retries use stable replay keys | Deterministic request IDs + explicit idempotent flag; durable deduplication remains Platform-owned |
| Local IPC | Same-user peer enforcement | SO_PEERCRED where supported |
| IPC resource use | Bounded request size/time | Daemon config |
| Local state | Durable SQLite | WAL + synchronous FULL |
| Task/run integrity | Dispatch only from durable OS task state | Task identity and Platform run lifecycle reconciliation |
| Database integrity | Referential integrity | SQLite foreign keys |
| Memory | Workspace/scope isolation | Durable record identity + retrieval predicates |
| Memory provenance | Source attribution + integrity chain | Provenance JSON + parent/content digests |
| Memory classification | Monotonic confidentiality ceiling | Retrieval admission |
| Memory trust | Instructions/facts/content/quarantine remain distinct | Trust-separated context assembly |
| Memory versioning | Stale writers fail closed | Expected-version + conflict policy |
| Memory retention | Automatic expiry plus explicit deletion | TTL/expiry + tombstone state |
| Memory poisoning | Suspicious persistent content is quarantined | Deterministic pre-persistence detector |
| Sensitive memory | Fail closed above caller clearance | Classification ceiling |
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


## M12 lifecycle controls

| Area | Control | Enforcement |
|---|---|---|
| Agent identity | Version binding | Durable `agents` row rejects version substitution |
| Lifecycle | Explicit transition graph | `AgentRuntime` state machine |
| State integrity | Optimistic concurrency | Expected state + state-version transaction |
| Event integrity | Atomic lifecycle event ledger | SQLite transaction + deterministic event ID |
| Heartbeat | Durable lease | Periodic heartbeat + persisted expiry |
| Crash recovery | Expired lease reconciliation | `recover_orphans` |
| Restart safety | Bounded restart count | Restart policy + fail-closed exhaustion |
| Authority | No local capability grants | Agent Platform remains authority plane |


## M13 developer-surface controls

| Area | Control | Enforcement |
|---|---|---|
| Manifest | Required identity/version/entrypoint fields | AgentManifest validation |
| Capability declaration | Declaration is descriptive, not authorization | SDK + Platform boundary |
| Capability integrity | Duplicate/empty requests rejected | CapabilityDeclaration validation |
| Approval | Approval references remain opaque | Platform adapter |
| Idempotency | Consequential SDK operations use deterministic or caller-supplied keys | Durable SDK idempotency ledger + Platform request key |
| Replay | Replayed operations return the recorded Platform reference | sdk_idempotency |
| Crash recovery | Claim survives process failure | SQLite durable transaction |
| Trace integrity | W3C traceparent is validated | TraceContext |
| Context isolation | Execution context is immutable | frozen SDK contracts + contextvars |
| Error handling | Platform failures remain typed and distinguishable | SDKPlatformError |
| Evidence | SDK exposes references but cannot create authoritative evidence | EvidenceRef |
| HTTP boundary | SDK does not construct Platform HTTP requests | AgentPlatformClient adapter |
| Authority | SDK cannot grant capabilities or approve itself | Platform remains authority |

The developer surface is intentionally designed around current agent-security concerns: identity and authorization, excessive agency, tool misuse, memory/context poisoning, supply-chain risk, and auditable agent actions. OWASP's 2026 Agentic Applications guidance identifies these as material risks, while NIST's agent identity work emphasizes explicit identity, authorization, delegation, human binding, auditability and non-repudiation.

## M14 model gateway controls

| Area | Control | Enforcement |
|---|---|---|
| Provider isolation | Provider adapters implement a typed provider protocol | `ModelProvider` |
| Model registry | Model descriptors are validated before registration | `ModelDescriptor.validate()` |
| Capability matching | Required features must be advertised by the selected model | Router admission |
| Task matching | Provider/model must advertise the requested task | Router admission |
| Cost policy | Application and request ceilings use the stricter bound | Router admission |
| Latency policy | Unknown latency is rejected when a latency ceiling is enforced | Router admission |
| Context policy | Input estimate + maximum output must fit the selected context window | Router admission |
| Privacy | Public/private/local levels are monotonic and the stricter requirement wins | Router admission |
| Allowlisting | Model/provider allowlists are intersected | Router admission |
| Fallback | Only transient provider failures may fall through to another candidate | Gateway failure model |
| Output trust | Model output is always untrusted data | `ModelResponse` boundary |
| Authority | No Platform authority contracts are imported by the gateway | Architecture test |
| Tracing | Validated W3C traceparent is propagated from immutable SDK context | SDK + gateway |
| Vision/speech | Unsupported future tasks fail explicitly | `UnsupportedModelTask` |

M14 therefore treats the model provider as an untrusted dependency from the perspective of consequential authority: a model can suggest an action, but only Agent Platform can authorize and execute that action.


## M15 context and trusted-memory controls

| Area | Control | Enforcement |
|---|---|---|
| Workspace isolation | Every memory record carries a workspace ID | Storage schema + retrieval predicate |
| Agent isolation | Records are bound to an agent | Retrieval predicate + access check |
| Session isolation | Working/session memory requires the active session ID | Scope contract + retrieval check |
| Task isolation | Task memory requires the active task ID | Scope contract + retrieval check |
| Long-term isolation | Long-term memory is workspace-scoped | Scope contract |
| Provenance | Source type/ID, actor, origin and collection time are persisted | MemoryProvenance |
| Integrity | Content/provenance/version chain is SHA-256 addressed | Memory digest + parent digest |
| Classification | Caller declares a maximum classification | Fail-closed retrieval ceiling |
| Trust | Trusted instructions are separated from verified facts and untrusted content | AssembledContext channels |
| Poisoning | Common persistent injection/exfiltration/security-bypass/key patterns trigger quarantine | Deterministic detector |
| Quarantine | Quarantined memory is excluded from ordinary retrieval | Explicit include_quarantined required |
| Versioning | Updates use compare-and-swap semantics | Expected version + conflict policy |
| Retention | Scope-specific defaults plus explicit TTL/expiry | Durable expiry timestamps |
| Deletion | Deleted records are tombstoned and excluded from active retrieval | State transition |
| Context assembly | Retrieval does not collapse trust classes into one prompt | Four-channel AssembledContext |
| Authority | Memory never creates Platform authority | Architecture boundary + no Platform grants |

OWASP's 2026 Agentic Applications material identifies memory/context poisoning as a distinct persistent attack surface and recommends origin tracking, access segmentation, retention limits, anomaly detection and rollback-oriented controls. M15 implements the repository-local portions of that boundary; semantic validation, external truth verification and enterprise retention policy remain deployment/application responsibilities.


## M25 forensic-hardening controls

| Area | Control | Enforcement |
|---|---|---|
| Release compatibility | Active version must satisfy manifest minimum supported version | Production release controller |
| Release evidence | Signature bundle, issuer, provenance and SBOM digest have strict shape validation | Release manifest validation |
| Staging safety | Failed backup preparation cannot leave a staged release behind | Update manager staged-release cancellation |
| Rollback correctness | Pre-activation failures do not invoke an unapplied-version rollback | Production controller state checks |
| Memory trust | Agent/external/import provenance cannot self-declare trusted instructions or verified facts | Memory store write boundary |
| Process environment | Loader/interpreter injection variables and non-allowlisted environment keys are rejected | Local process supervisor |
| Fleet endpoints | Unix sockets require absolute local paths; HTTPS endpoints require an authority | Fleet registry |
| CI supply chain | All workflow action references must resolve to immutable 40-hex commit SHAs | CI workflow pinning gate |

The hardening layer preserves the same authority boundary: these controls constrain local composition and release integrity; they do not replace Agent Platform authorization, enterprise identity, sandboxing, signing infrastructure or centralized evidence.
