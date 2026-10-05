# Phase 4 — Canonical Ontology

The canonical semantic hierarchy is:

~~~text
Domain
  -> Capability Family
      -> Capability
          -> Skill
              -> Agent Profile
                  -> Agent Instance
~~~

Roles and archetypes are orthogonal semantic nodes. Tools, environments and protocols are typed constraints/resources rather than agents.

## Rules

- Stable ontology IDs are namespaced and typed.
- Parent-child relationships are type checked.
- Capabilities describe work, never permission.
- Skills refine capabilities.
- Roles and archetypes never imply authority.
- Relations are descriptive and do not execute.
- Agent profiles bind implementations in Phase 7.
- Authority remains Platform-owned.

The implementation lives in src/tinlance_agent_os/catalog_ontology.py. Schema serialization is deliberately deferred to Phase 5.

## Phase gate

The ontology module and unit tests must pass across supported Python versions before Phase 5.
