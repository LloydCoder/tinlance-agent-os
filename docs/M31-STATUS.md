# M31 — Connectors & Data Spaces

M31 introduces connector lifecycle contracts for filesystem, Git, database, object storage, HTTP API, SaaS, messaging, knowledge and MCP data spaces.

Connectors own registration, endpoint validation, lifecycle state, capabilities metadata and synchronization cursors. They do not grant authority or execute consequential actions.

MCP remains an interoperability protocol; Agent OS owns connector lifecycle and persistence around it. The current MCP 2026-07-28 specification is explicitly designed around stateless operation and separately defined Tasks, reinforcing the boundary between protocol transport and OS lifecycle. citeturn6search2turn6search1


CI refresh: branch is rebased onto the corrected connector source.
