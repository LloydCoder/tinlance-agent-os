Agent Catalog v3 — Phase 35: GA / Continuous Taxonomy Evolution

Phase 35 establishes the general-availability governance contract for continuous taxonomy evolution after the 20K strategic milestone.

## Continuous evolution model

Catalog releases are immutable evidence-bearing snapshots. Each evolution release records a base inventory digest, proposed inventory digest, explicit additions, explicit deprecations, and governance evidence.

The model is append-and-deprecate rather than destructive deletion. Deprecated canonical identifiers remain historically addressable; they are removed from the active canonical set through the governed lifecycle.

## Release invariants

- every evolved record is CANONICAL or DEPRECATED;
- every evolved record retains review evidence;
- additions and deprecations cannot overlap in one release;
- addition/deprecation identifier lists are unique and deterministic;
- release and inventory digests are deterministic;
- governance evidence is mandatory;
- preparing a release does not publish it or grant authority.

## Operating model

DISCOVERED → NORMALIZED → CLUSTERED → CANDIDATE → VALIDATED → REVIEWED → CANONICAL remains the only publication lifecycle.

Continuous discovery may propose candidates, but deterministic validation and governance review remain required before canonical publication. Evaluation, trust classification, A2A/MCP metadata, release gates, and forensic validation remain separate concerns.

## Authority boundary

Catalog GA does not replace Platform, Directory, Registry, or M17 coordination. It describes and qualifies taxonomy; Platform remains the authority for runtime admission, authorization, approvals, execution, delegation, budgets, sandboxing, evidence, and audit.

## GA acceptance criteria

- 420 seed taxonomy remains historical rather than a permanent ceiling;
- strategic 20K canonical milestone is governed by fixed proof controls;
- continuous discovery and evolution are deterministic and evidence-bearing;
- no synthetic provider/model/locale/tool combinations inflate taxonomy identity;
- prior phase forensic gates remain part of the release discipline;
- CI and architecture boundaries remain green.

## Final gate

Phase 35 may merge only after exact-head CI is green. After merge, a final post-merge forensic audit must confirm the complete Phase 21–35 sequence and GA invariants. Only then is the Agent Catalog v3 sequence considered closed.
