# ADR-0003: Domain Products Are Integrations

## Decision

FAS, FAS-Bench, FDSE, TADS, ThreatFade, Hezqara and other Tinlance products do not become
Agent OS core dependencies.

They may integrate through explicit adapters.

## Rationale

This preserves a reusable operating environment and prevents product-specific authority,
intelligence or security assumptions from entering the OS kernel.
