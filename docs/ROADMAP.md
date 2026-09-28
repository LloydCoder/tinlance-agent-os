# Roadmap

## M0 — Architecture Foundation

- Domain contracts for user, workspace, session, agent, task, run and event.
- Stable Agent Platform integration boundary.
- OS authority/non-authority invariants.
- Session versus Platform run separation.
- System abstraction boundary.
- Security threat model.
- Architecture and dependency tests.
- CI quality/security gates.

## M1 — Agent Platform Adapter

Implement a production-quality adapter against the Agent Platform public API/SDK,
with contract tests and compatibility checks.

## M2 — Local Agent OS Daemon

Introduce the local control daemon and agent lifecycle management.

## M3 — Workspace, Session and Task System

Persist and manage workspaces, sessions, tasks, artifacts and task/run relationships.

## M4 — Workflow Composition

Add deterministic workflow graphs, dependencies and human checkpoints.

## M5 — Context and Memory

Add context and memory orchestration without turning memory into authority.

## M6 — Agent Application Model

Define agent manifests, packaging, lifecycle and capability requests.

## M7 — System Integration

Add filesystem, process, notification, desktop and networking abstractions/adapters.

## M8 — Desktop/Shell

Build the primary Agent OS user experience.

## M9 — Extensions

Add a governed extension/plugin model.

## M10 — Enterprise / Remote OS

Add multi-user administration, SSO, fleet management and remote agent control.

## M11 — Production Distribution

Packaging, updates, recovery, installation and operational hardening.
