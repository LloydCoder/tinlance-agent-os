# Tinlance Agentic OS Architecture

## Boundary

Tinlance Agentic OS is the human/agent/organization environment above Tinlance Agent
Platform. It owns workspaces, sessions, tasks, workflows, applications, presentation,
and system integration. Tinlance Agent Platform owns authority and governed execution.

## Dependency direction

`contracts -> domain -> services -> integrations -> apps`

The Agent Platform integration is an adapter boundary. OS code must not import Agent
Platform implementation internals.

## Authority boundary

`User intent -> OS task -> Platform request -> Platform authorization/policy/approval
-> Platform execution -> Platform evidence/events -> OS presentation`

Agent OS may compose and request work. It may not independently authorize consequential
actions.

## Agent Platform API v1.1

The OS adapter uses a provider-neutral transport and the Platform v1.1 request/response envelope.

Supported operations:

- principal.get
- agents.list
- runs.create
- runs.cancel
- capabilities.list
- approvals.request
- runs.events
- runs.evidence
- health

Request identity is propagated with tenant/subject context, a fresh X-Request-ID, optional W3C traceparent, and a bearer credential. Non-idempotent run creation, cancellation and approval requests are never automatically retried.

The Platform is authoritative for identity, tenant membership, authorization, policy and approval. Agent OS treats returned approval and evidence identifiers as opaque references.

## Core M0 objects

- User
- Workspace
- Session
- Agent
- Task
- Run reference
- Capability reference
- Approval reference
- Evidence reference
- Event

An OS Session is not a Platform Run. A session may contain multiple tasks and a task may
produce multiple Platform runs.

## Planes

### Experience plane
CLI, future desktop, workspace and human interaction.

### OS control plane
Agent lifecycle, sessions, tasks, workflows and context.

### Platform authority plane
Identity, tenancy, authorization, policy, approvals, budgets and governed execution.
This remains in Agent Platform.

### Evidence/telemetry plane
Platform evidence/events plus OS correlation and presentation. The OS does not replace
Platform evidence authority.

## Future integration model

```
Agentic OS
   |
   +-- Agent Platform adapter
   +-- FDSE adapter
   +-- FAS adapter
   +-- TADS adapter
   +-- domain/product adapters
   |
   +-- System abstractions
```

Domain products remain optional integrations and never become Agent OS core dependencies.

## Current implementation boundary

M0–M11 repository capabilities are implemented and tested. The following are intentionally deployment/provider seams rather than missing repository features: enterprise IdP/SSO, hosted fleet control, production telemetry backend, artifact signing service, desktop toolkit, durable Platform infrastructure and production sandbox supervision.

The historical M0 non-goals below are retained only as historical scope notes; they do not override the current roadmap or implementation.

## M0 historical non-goals

- desktop shell
- workflow engine implementation
- memory/vector database
- extension runtime
- Linux process sandbox
- direct model-provider integration
- replacement authorization engine
- replacement evidence/audit store
