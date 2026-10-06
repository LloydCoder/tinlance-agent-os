# Agent Catalog v3 — Phase 32: A2A/MCP Interoperability Mapping

Phase 32 maps interoperability metadata into the Catalog without turning external protocol declarations into authority.

## A2A

A2A Agent Cards are mapped as descriptive agent metadata: identity, protocol version, capabilities, skills, interfaces, input/output modes, security schemes, and signature presence. A2A 1.0 defines Agent Cards for discovery and requires authorization checks on protocol operations. https://a2a-protocol.org/dev/specification/agent-card/

Catalog mapping therefore never authenticates a caller, grants permissions, or admits an external agent to the Tinlance runtime.

## MCP

MCP server primitives are mapped as tool-provider metadata. Tools, resources, and prompts are represented as provider capabilities/skills, but an MCP server is never promoted into an Agent Catalog archetype merely because it exposes protocol primitives.

This preserves the architecture boundary: MCP supplies tools/resources; Agent Catalog describes agents and capabilities; Platform controls authority.

## Hard controls

- protocol and identity versions are required;
- descriptive capabilities and skills cannot contain blank values;
- production interfaces must be HTTPS or gRPC;
- A2A mappings require descriptive skills;
- MCP mappings are structurally constrained to the tool-provider class;
- fingerprints are deterministic;
- signatures are metadata and do not imply trust or authorization.

## Security boundary

No network request, endpoint invocation, credential acquisition, execution, authorization, Directory mutation, Registry publication, or delegation occurs in this module.

## Gate

Phase 32 may merge only after exact-head CI is green. After merge, a controlled post-merge forensic audit must verify the A2A/MCP boundary and then unlock Phase 33.
