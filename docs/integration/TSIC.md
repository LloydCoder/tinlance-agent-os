# TSIC Integration

Agent OS is the workspace, environment, lifecycle, orchestration, UX, builder, and fleet layer. Agent Platform remains the consequential execution authority.

TSIC is the canonical ecosystem integration and certification authority. The Agent OS CI gate consumes immutable TSIC revision ae53c58afd78b48b1f0b95640ca0db698018cd7d and verifies repository identity, governance role, contract bindings, and authority invariants.

Run locally:

    python scripts/tsic_conformance.py

The gate is verification-only. It does not grant execution authority and does not replace the Platform authorization boundary.
