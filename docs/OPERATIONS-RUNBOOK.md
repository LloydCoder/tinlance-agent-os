# Production Agent OS Runbook

## Release flow

1. Merge only green changes to main.
2. Create an annotated version tag matching vMAJOR.MINOR.PATCH.
3. The production workflow builds the wheel and sdist from the tagged revision.
4. CycloneDX SBOM is generated.
5. Release artifacts are signed with Sigstore/Cosign keyless signing.
6. GitHub artifact attestations generate signed SLSA/in-toto provenance and SBOM attestations.
7. SHA-256 checksums are published with the release.
8. Deployment consumes a ReleaseManifest and verifies signature, provenance and SBOM before activation.

## Staged rollout

Use canary for the first cohort and stable only after health checks pass. The production controller performs repeated health checks after activation.

## Automatic rollback

A failed health check or migration exception triggers release quarantine, rollback to the previously active version, backup restoration, and terminal ROLLED_BACK state.

## Database migrations

Every migration must have a stable migration ID and be reversible or paired with a verified backup/restore procedure. Backups are created before migration.

## Disaster recovery

Maintain versioned release artifacts, signed checksums, provenance and SBOM attestations, durable backups, restore verification, and documented recovery ownership. A disaster-recovery exercise must prove restoration into a clean environment rather than merely proving that a backup file exists.

## Health checks

Minimum release health signals: process start, Platform connectivity, storage connectivity, workflow recovery, model gateway availability, remote runtime health where enabled, and telemetry export health.

## Security response

Quarantine the affected version first. Preserve the signed artifact, SBOM, provenance, logs and relevant trace identifiers. Freeze promotion of the affected channel, rotate compromised signing or deployment credentials where applicable, publish a corrected release, and record the incident and remediation.

## Downgrade policy

The runtime rejects same-version and lower-version artifacts. Emergency rollback is an explicit controller operation using a previously verified active version and backup, not a normal release downgrade.

## Release verification

Consumers should verify the published checksum, Sigstore bundle, and GitHub artifact attestation before installing.