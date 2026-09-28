# M0 Threat Model

## Assets

- user identity and workspace boundaries
- task/session metadata
- Platform run references
- evidence references
- capability/approval references
- credentials and secrets handled by downstream Platform services

## Threats

- privilege escalation through OS task state
- tenant confusion or cross-workspace data leakage
- treating model output as authority
- bypassing Platform approvals
- direct imports of Platform internals creating security drift
- malicious or compromised extensions
- memory/context poisoning in later milestones
- replay or confusion of stale run/event references

## M0 mitigations

- explicit typed identifiers
- stable Platform integration boundary
- no local authorization authority
- architecture tests preventing internal Platform imports
- correlation IDs and Platform run references
- security invariants documented before higher-level features

## Residual risk

M0 does not provide production isolation, persistence, authentication or extension
sandboxing. Those belong to later milestones and the Agent Platform deployment boundary.
