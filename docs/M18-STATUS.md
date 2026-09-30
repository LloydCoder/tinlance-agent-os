# M18 — Agent Ecosystem Runtime

**Status: COMPLETE**

M18 establishes a verified package boundary for skills, applications, extensions, connectors and agent packages.

Implemented:
- typed package manifests;
- artifact SHA-256 verification;
- signature verification;
- provenance metadata;
- exact dependency/version resolution;
- capability requirements;
- Platform-authorized capability grants;
- quarantine;
- rollback to previously verified artifacts;
- lifecycle state;
- adversarial package trust tests.

Security invariant: a package manifest, caller claim, dependency declaration or local metadata cannot create Platform authority.