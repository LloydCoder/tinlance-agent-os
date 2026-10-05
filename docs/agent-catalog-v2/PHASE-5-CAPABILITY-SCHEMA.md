# Phase 5 — Capability Schema

## Contract

The versioned CapabilityProfile schema is the machine-readable boundary between the canonical ontology and installed/remote agent implementations.

It records:
- stable identity and version;
- domain and capabilities;
- skills, inputs and outputs;
- tools, environments and modalities;
- A2A/MCP protocol compatibility;
- model metadata;
- risk and autonomy;
- approval and data-sensitivity requirements;
- bounded delegation metadata;
- evidence/evaluation requirements;
- trust and evaluation scores;
- operational cost and latency;
- provenance, artifact digest, signature and SBOM references;
- compatibility and lifecycle status.

## Authority boundary

Profile declarations are descriptive. They do not grant capabilities or authorization. Effective authority is decided by Agent Platform at execution admission.

## Validation

The schema fails closed for:
- missing identity/domain/capability;
- invalid risk/autonomy values;
- negative delegation limits;
- delegation limits when delegation is disabled;
- missing provenance;
- out-of-range trust/evaluation scores;
- negative cost/latency.

Profiles serialize to the versioned tinlance.agent-profile.v2 record and reject unsupported schema versions.

## Gate

Phase 5 is complete only when schema unit/contract tests and the complete CI matrix are green.
