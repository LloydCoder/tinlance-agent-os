# M13 Agent SDK / Application SDK — Completion Record

**Status: COMPLETE**

M13 is the official high-level developer surface above the Agent Platform client and M12 lifecycle runtime.

## Implemented

- AgentSDK and AgentApplication scaffolding;
- validated AgentManifest and CapabilityDeclaration contracts;
- lifecycle/runtime construction through M12;
- session and task helpers;
- workflow construction/completion/failure/cancellation helpers;
- Platform-backed approval workflows;
- typed ExecutionResult with PlatformRunRef, Event and EvidenceRef;
- structured SDK and Platform error boundaries;
- deterministic and caller-supplied idempotency keys;
- durable SQLite idempotency claims and completion records;
- replay-safe run creation and approval requests;
- immutable ExecutionContext and W3C traceparent validation;
- trace-context propagation into the concrete Platform adapter;
- public SDK exports;
- golden-path reference-agent tests;
- idempotency/replay, approval, workflow, context, manifest and capability conformance tests;
- README, roadmap, architecture, security controls and Platform integration documentation reconciled.

## Authority boundary

M13 does not authorize capabilities, mint grants, validate approvals, issue secrets, execute tools, enforce policy, enforce budgets, or create authoritative evidence. Those remain Tinlance Agent Platform responsibilities.

## Golden path

    scaffold -> runtime -> register -> session -> task -> execute -> result

A developer can construct and operate a reference agent through the high-level SDK without constructing low-level Platform HTTP requests.

## Reliability

Consequential SDK operations claim a durable idempotency key before contacting Platform and send the same key to Platform. A completed claim replays the recorded Platform reference. An interrupted claim can be retried with the same logical key. Platform-side idempotency remains the final protection against duplicate consequential side effects.

## Verification

M13 is accepted only when repository CI passes formatting, lint, strict typing, tests/coverage, dependency audit and architecture/security gates across Python 3.12, 3.13 and 3.14.
