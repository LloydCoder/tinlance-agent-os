# Agent OS M0 Threat Model

## Scope

M0 covers the boundary between the Tinlance Agentic OS and the Tinlance Agent Platform.
The OS is an environment and composition layer; the Platform remains the authority and
governed execution layer.

## Trust boundaries

User -> OS UI/CLI -> OS daemon/services -> Agent Platform -> tools/MCP/sandbox/external systems.

## Untrusted inputs

The OS must treat model output, retrieved content, tool responses, external content,
extension-provided data and peer-agent messages as untrusted data. None can create
authority, change tenant context, or bypass Platform authorization.

## Security invariants

1. Agent OS never grants execution authority.
2. Agent OS never treats model output as authorization.
3. Consequential work is requested through the Agent Platform boundary.
4. Platform approval references are opaque to the OS; the OS does not validate them
   as a substitute for Platform authorization.
5. Platform evidence is referenced, not rewritten as OS security evidence.
6. OS identifiers are correlation and lifecycle identifiers, not authorization claims.
7. Future extensions must request capabilities through the governed Platform boundary.
8. System access is abstracted and must not be silently available to arbitrary agents.

## Threats

| Threat | M0 control |
|---|---|
| Authority escalation | Platform is the sole execution authority |
| Prompt injection | Untrusted content cannot create OS authority |
| Confused deputy | Workspace/session identifiers do not authorize actions |
| Cross-workspace access | Future adapters must preserve immutable context |
| Approval bypass | OS stores references; Platform validates approvals |
| Evidence forgery | Platform remains evidence authority |
| Extension abuse | Extension boundary is only defined, not privileged |
| Local system escape | System provider is an abstraction, not direct agent access |

## Residual risk

M0 does not claim production isolation, durable persistence, authentication implementation,
or Linux system enforcement. Those are later milestones/deployment responsibilities.
