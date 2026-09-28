# ADR-0002: Session Is Not a Platform Run

## Decision

An Agent OS session is a human-facing context. A Platform run is a governed
execution instance.

## Consequences

One session may contain multiple tasks and multiple Platform runs. The OS
maintains the relationship but does not substitute its task/session state for
Platform execution state.
