# ADR-0002: OS Session Is Distinct From Platform Run

## Decision

An Agent OS session represents a human/agent interaction context. A Platform run represents
a governed execution instance.

One session may contain many tasks and one task may result in multiple Platform runs.

## Rationale

This prevents UI/session lifecycle from becoming an accidental execution authority model and
allows retries, approvals, delegation and future workflow composition without conflating state.
