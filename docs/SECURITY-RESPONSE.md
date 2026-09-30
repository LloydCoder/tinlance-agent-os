# Security Response Procedure

## Trigger conditions

Trigger release response for signature or provenance verification failure, SBOM integrity mismatch, artifact tampering, credential or signing-key compromise, critical dependency exposure, unexplained production health regression, or suspected malicious extension/supply-chain artifact.

## Containment

1. Quarantine the affected release version.
2. Freeze promotion of the affected release channel.
3. Preserve artifact, SBOM, provenance and relevant telemetry.
4. Revoke or rotate compromised credentials/keys.
5. Stop automated rollout if still in progress.

## Recovery

Restore the last verified release and associated backup. Validate health and recovery before reopening the channel.

## Eradication and lessons learned

Identify the compromised artifact or dependency, rebuild from a clean revision, regenerate SBOM/provenance, sign the replacement release, rerun the M23 adversarial suite, and document the incident.

## Evidence

Keep immutable references to the release digest, signature bundle, provenance attestation, SBOM, CI workflow and commit, deployment event, and rollback/backup identifiers.

The response process must not treat model output or unverified agent claims as security evidence.