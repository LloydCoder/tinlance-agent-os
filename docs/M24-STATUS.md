# M24 — Production Agent OS

**Status: Complete.**

M24 provides production distribution controls including signed-artifact/provenance integration seams, SBOM references, staged channels, health-gated deployment and rollback/update controls.

Boundary: signing, provenance services, artifact repositories and OS service management remain deployment infrastructure.

Acceptance:
- release bytes are integrity checked;
- staged/apply/rollback transitions are explicit;
- downgrade and migration safety are enforced;
- external signing/provenance remain explicit deployment responsibilities.
