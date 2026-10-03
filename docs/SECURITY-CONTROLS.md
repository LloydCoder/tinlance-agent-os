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


## M29 scheduler controls

| Area | Control | Enforcement |
|---|---|---|
| Schedule identity | Schedule IDs and workspace IDs are persisted together | Scheduler schema + workspace foreign key |
| Time handling | Persisted times are UTC-normalized; cron/calendar timezones must be valid IANA zones | Scheduler |
| Replay/deduplication | Job IDs are deterministic from schedule + scheduled occurrence | SHA-256 job identity |
| Misfires | Missed schedules use explicit skip/run-once/catch-up semantics | Scheduler policy |
| Concurrency | A schedule cannot exceed its configured running-job limit | Lease admission query |
| Worker recovery | Expired leases return jobs to queued state | Durable lease expiry |
| Generation safety | Schedule updates require the expected generation | Store CAS update |
| Failure durability | Dispatcher failures become terminal job failures | Job state transition |
| Authority | Scheduling never grants capability or authorization | Architecture boundary |
| Distributed boundary | Local leases are not claimed as distributed exactly-once | M29/M38 separation |

The scheduler is an OS lifecycle mechanism. It is not an authorization engine, approval engine or execution authority. A scheduled job must still traverse the normal Task/Workflow path and Agent Platform authority boundary before consequential work occurs.


## M30 knowledge controls

- knowledge sources are workspace-bound;
- documents carry content digests, source versions, collection times and validity windows;
- classification and trust are explicit retrieval filters;
- quarantined content cannot enter the active fabric;
- provenance is returned with every retrieved hit;
- context assembly has a deterministic size budget;
- retrieval never creates capabilities, approvals or authorization;
- semantic/vector backends must preserve the same provenance/trust contract;
- external content is treated as data and must not be interpreted as an authority-bearing instruction.


## M33 evaluation controls

| Area | Control | Enforcement |
|---|---|---|
| Case integrity | Version and input digest are required | EvaluationCase validation |
| Run isolation | Runs carry workspace identity and suite identity | Durable run schema |
| Measurement integrity | Measurement identity is unique per run/case/metric | Database uniqueness constraint |
| Unit safety | Gates require exact metric unit agreement | Gate evaluator |
| Fail-closed quality gates | Missing observations cannot pass | Gate evaluator |
| Temporal integrity | Naive timestamps are rejected and stored timestamps are UTC-normalized | EvaluationRuntime |
| Comparison determinism | Baseline/candidate deltas are ordered by metric and use integer values | compare_runs |
| Evidence boundary | Evidence references are opaque metadata | EvaluationMeasurement |
| Authority | Evaluation cannot grant capabilities, authorize actions or enforce Platform budgets | Architecture boundary |
| External benchmarks | FAS/FAS-Bench integrate through data/contracts rather than kernel imports | Dependency boundary |


## M34 fleet control-plane controls

| Area | Control | Enforcement |
|---|---|---|
| Device identity | Device and endpoint IDs are required and endpoint IDs are unique | Fleet schema + validation |
| Workspace isolation | Devices, groups and deployments carry workspace identity; membership and deployment joins verify it | FleetControlPlane |
| Generation safety | Device state/configuration updates require expected generation | CAS-style generation check |
| Health safety | Placement only considers enrolled/online devices | Placement planner |
| Capacity safety | Negative and overcommitted capacity is rejected | FleetDevice validation |
| Rollout state | Agent/version/cohort desired state is durable | FleetDeployment |
| Attestation | Attestation is an opaque reference, not a local trust decision | FleetDevice |
| Authority | Fleet planning cannot grant capabilities or execute consequential actions | Architecture boundary |
| Hosted seam | Centralized control plane and device-management services remain deployment integrations | M34 boundary |


## M35 device operating-environment controls

| Area | Control | Enforcement |
|---|---|---|
| Image integrity | OS images require lowercase 64-hex SHA-256 digests | OSImage validation |
| Boot posture | Secure Boot, TPM and disk-encryption requirements are explicit profile fields | DeviceSecurityProfile |
| Desired-state safety | Device image changes use generation checks | DeviceOSRuntime |
| Update identity | Update IDs are unique and source/target no-op updates are rejected | Durable schema + validation |
| Recovery | Recovery image is modeled separately from target image | OSUpdate |
| Provenance | Image provenance is represented as an opaque reference | OSImage |
| Rollback | Update lifecycle includes explicit rolled-back state | UpdateState |
| Distribution boundary | Kernel, bootloader, firmware, TPM and encryption services remain external | M35 deployment seam |
| Authority | Device update metadata cannot grant capabilities or authorize agent work | Architecture boundary |


## M36 marketplace and registry controls

| Area | Control | Enforcement |
|---|---|---|
| Publisher trust | Blocked publishers cannot register packages | AgentRegistry |
| Artifact integrity | Versions require strict SHA-256 digests | RegistryVersion validation |
| Signature | Published versions require a signature reference | RegistryVersion validation |
| Provenance | Provenance and SBOM are explicit opaque references | RegistryVersion |
| Lifecycle | Quarantine/revocation/deprecation are durable states | Registry schema |
| Generation safety | Version state changes require expected generation | set_version_state |
| Identity | Package/version duplicates are rejected | Unique constraints |
| Execution boundary | Registry never executes package code | Architecture boundary |
| Authority | Installation/capability grants remain Platform-governed | Platform integration |


## M37 operator-plane controls

| Area | Control | Enforcement |
|---|---|---|
| Projection isolation | Every operator entity carries workspace identity | Operator schema |
| Projection integrity | Entity generations advance on replacement | OperatorPlane |
| Query safety | Workspace is mandatory; optional filters are parameterized | list_entities |
| Command integrity | Commands require entity/action/parameter digest identity | OperatorCommand validation |
| Command uniqueness | Command IDs are unique | Database constraint |
| Time integrity | Naive timestamps are rejected | OperatorPlane |
| Authority boundary | Commands are intents only; no local execution or authorization | Architecture boundary |
| Source of truth | Operator data is a projection of owning runtimes | M37 design |


## M38 reliability controls

| Area | Control | Enforcement |
|---|---|---|
| Persistence | Deployment mode explicitly distinguishes local SQLite from distributed PostgreSQL | ReliabilityProfile |
| Regional resilience | Distributed mode requires at least two regions | Profile validation |
| Worker coordination | Active worker/resource leases are unique | Lease schema |
| Lease safety | Lease release uses generation checks | release_lease |
| Temporal safety | Lease expiry must be future and timezone-aware | _timestamp + validation |
| DR | Backup and restore targets are explicit with RPO/RTO | DRPlan |
| Chaos | Scenario kind and blast radius are explicit | ChaosScenario |
| Readiness | Reliability readiness is derived from durable state | readiness |
| Authority | Reliability controls do not grant capabilities or execute customer work | Architecture boundary |


## M39 enterprise security and compliance controls

| Area | Control | Enforcement |
|---|---|---|
| Enterprise identity | OIDC/SAML/SCIM protocol is explicit | SecurityIntegration |
| Key management | Provider and key references are explicit opaque identifiers | KeyProvider |
| Audit export | Destination, scope and retention are durable | AuditExport |
| Data governance | Residency, retention, deletion window and legal hold are explicit | DataPolicy |
| Incident response | Incident IDs and evidence export references are durable | SecurityIncident |
| Revision safety | Data-policy generations advance deterministically | set_data_policy |
| Tenant isolation | All records are workspace scoped | Security schema |
| Authority | External IdP/KMS/audit services and Agent Platform retain authority | M39 boundary |


## M40 adaptive-runtime controls

| Area | Control | Enforcement |
|---|---|---|
| Observation identity | Observation, workspace and policy IDs are required | AdaptiveObservation validation |
| Metric safety | Unit and sample size are explicit; empty units and non-positive samples fail | AdaptiveObservation validation |
| Workspace isolation | Observations must match their policy workspace | AdaptiveRuntime |
| Recommendation explainability | Recommendation stores objective, metric, target, observed value and reason | AdaptiveRecommendation |
| Recommendation lifecycle | Proposed/accepted/rejected/expired state is durable | Adaptive schema |
| Decision safety | Accepted/rejected transitions require expected generation | decide |
| Adaptive authority | Recommendations cannot grant capabilities, approve actions or execute work | Architecture boundary |
| Reversibility | Recommendations remain intents until an owning runtime validates and dispatches them | M40 boundary |
| Telemetry integrity | Adaptive inputs should come from validated OS/Platform telemetry, not model assertions | Integration boundary |
| Sensitive data | Recommendation reasons should reference metric metadata rather than raw prompts, secrets or confidential memory | Observability/data-minimization policy |


## M41 enterprise GA and assurance controls

| Area | Control | Enforcement |
|---|---|---|
| Release identity | Version/API/schema identity is explicit | GARelease |
| Artifact integrity | Artifact digest is required | GARelease |
| Supply-chain evidence | SBOM and provenance references are required | GARelease |
| Assurance evidence | Passed/failed checks require evidence references | GACheck |
| Readiness | Pending or failed checks block GA readiness | EnterpriseGARuntime |
| Compatibility | Component support ranges are durable | GACompatibility |
| External certification | Repository does not self-assert SOC 2/ISO/pentest completion | M41 boundary |
| Governance mapping | NIST CSF 2.0 functions are treated as assurance mapping, not implementation claims | Documentation |
| Provenance | Production release must preserve verifiable provenance references | Release pipeline |
| Authority | GA readiness cannot grant capabilities or authorize execution | Architecture boundary |
