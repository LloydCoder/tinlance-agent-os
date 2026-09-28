# Tinlance Agentic OS — Architecture

## Purpose

Tinlance Agentic OS is the higher-level agent-native operating environment. It owns
human/agent interaction, workspaces, sessions, tasks, workflows, applications and
system integration. It does not own execution authority.

## System boundary

Human / Organization
  -> Tinlance Agentic OS
  -> stable public contract/API
  -> Tinlance Agent Platform
  -> tools / MCP / sandbox / models / external systems

## Authority invariant

Agent OS can request, compose, display, schedule and cancel work. It cannot
independently grant authority for consequential actions.

The Agent Platform remains the authority boundary:
principal -> tenant -> capability -> policy -> approval -> execution -> evidence

Model output, retrieved content, tool output and peer-agent messages are untrusted data.

## Dependency direction

contracts -> domain -> services -> integrations -> apps

Agent OS must not import internal implementation modules from Agent Platform.
The agent-client/integration boundary is the only supported coupling.

## Session versus run

An OS session is a human-facing context that can contain many tasks. A Platform
run is a governed execution instance.

Session -> Task -> Platform Run(s)

These objects must not be conflated.

## Domain product boundary

FDSE, FAS, FAS-Bench, TADS, ReconOS, ThreatFade, Hezqara and other domain
products are consumers/integrations. They are not dependencies of the Agent OS core.
