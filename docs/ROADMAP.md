# Agent OS Roadmap

## M0 — Architecture Foundation

Establish domain contracts, dependency boundaries, Platform adapter contract, security model,
CI and architecture tests.

## M1 — Agent Platform Adapter

Implement a transport-backed adapter against the stable Platform API/SDK. Add contract,
authentication, lifecycle, events, evidence and approval-reference integration.

## M2 — Local Agent OS Daemon

Provide a local control service for lifecycle, sessions, task dispatch and event handling.

## M3 — Workspace, Sessions and Tasks

Implement durable OS-level workspace/session/task state and clear mapping to Platform runs.

## M4 — Workflow Engine

Add task dependencies, checkpoints, human input and governed multi-step composition.

## M5 — Context and Memory

Add scoped context and memory abstractions with explicit trust/classification boundaries.

## M6 — Agent Application Model

Define manifests, packages, lifecycle, compatibility and capability requests.

## M7 — System Integration

Implement filesystem, process, notification, networking and desktop abstractions through
the Tinlance Computing Platform boundary.

## M8 — Desktop/Shell

Build the user-facing Agent OS desktop experience.

## M9 — Extensions

Implement a governed extension runtime and SDK.

## M10 — Enterprise

Add remote agents, fleet management, SSO, organization/workspace administration and
enterprise operational controls.

## M11 — Production Distribution

Package, update, release, recovery and operationalize the complete Agent OS.
