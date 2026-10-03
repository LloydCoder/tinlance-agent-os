# M35 — Device / Desktop Operating Environment

## Status

**Complete** — repository-owned device security profiles, OS image metadata, desired image state, update lifecycle, tests and documentation are implemented.

## Deployment reference

M35 is a device deployment profile, not a Linux distribution. A production Tinlance device can use an image-based Linux design with Secure Boot, signed boot artifacts, TPM-backed disk encryption, verified filesystem content and rollback-capable updates. The Python core deliberately models the contracts while firmware, bootloader, key infrastructure, image builders and device agents remain deployment components.

## Acceptance

- security posture is explicit and durable;
- OS image identity requires a strict SHA-256 digest;
- desired image changes are generation protected;
- update records are unique and source/target no-op updates fail closed;
- update lifecycle supports staged, active, failed and rolled-back states;
- recovery image references are explicit;
- device OS state cannot grant Agent Platform authority.

## Boundary

M34 owns fleet-level device desired state. M35 owns device-side OS deployment semantics. Agent Platform remains the authority for identity, authorization, approvals and consequential execution.
