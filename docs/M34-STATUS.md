# M34 — Enterprise Fleet & Remote Control Plane

**Status: Complete.**

M34 provides durable device inventory, fleet groups, desired agent deployment state, rollout cohorts, health/draining/quarantine state and deterministic placement planning.

Boundary: M34 is a control-plane contract, not a replacement for Platform identity/authorization or a hosted MDM/attestation service.

Acceptance:
- devices and deployments are workspace scoped;
- generations protect mutable state;
- placement respects enrollment/health/capacity constraints;
- attestation remains an opaque external reference;
- consequential work still traverses Platform governance.
