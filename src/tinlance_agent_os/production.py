"""Production release control plane primitives.

The controller consumes externally verified Sigstore/in-toto/SBOM evidence. It
does not implement a parallel signing authority; deployment policy remains
explicit and fail-closed.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Protocol

from .distribution import ReleaseArtifact, UpdateManager


class ReleaseChannel(StrEnum):
    CANARY = "canary"
    BETA = "beta"
    STABLE = "stable"


class ReleaseState(StrEnum):
    VERIFIED = "verified"
    STAGED = "staged"
    ROLLING_OUT = "rolling_out"
    HEALTHY = "healthy"
    ROLLED_BACK = "rolled_back"
    QUARANTINED = "quarantined"
    FAILED = "failed"


class ProductionReleaseError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class SignatureEvidence:
    bundle_uri: str
    signer_identity: str
    issuer: str


@dataclass(frozen=True, slots=True)
class ProvenanceEvidence:
    predicate_type: str
    source_repository: str
    source_revision: str
    build_workflow: str


@dataclass(frozen=True, slots=True)
class SBOMEvidence:
    format: str
    digest: str
    uri: str


@dataclass(frozen=True, slots=True)
class ReleaseManifest:
    artifact: ReleaseArtifact
    channel: ReleaseChannel
    signature: SignatureEvidence
    provenance: ProvenanceEvidence
    sbom: SBOMEvidence
    minimum_version: str = "0.0.0"
    migration_id: str | None = None

    def validate(self) -> None:
        if self.sbom.format.lower() not in {"cyclonedx", "spdx"}:
            raise ProductionReleaseError("unsupported SBOM format")
        if not self.signature.signer_identity.strip() or not self.signature.issuer.strip():
            raise ProductionReleaseError("release signature identity is required")
        if not self.provenance.source_repository.strip() or not self.provenance.source_revision.strip():
            raise ProductionReleaseError("release provenance is incomplete")
        if not self.provenance.predicate_type.startswith("https://"):
            raise ProductionReleaseError("release provenance predicate must be a URI")


class ReleaseVerifier(Protocol):
    def verify_signature(self, manifest: ReleaseManifest, data: bytes) -> bool: ...
    def verify_provenance(self, manifest: ReleaseManifest) -> bool: ...
    def verify_sbom(self, manifest: ReleaseManifest) -> bool: ...


class HealthChecker(Protocol):
    def check(self, *, version: str, channel: ReleaseChannel) -> bool: ...


class BackupStore(Protocol):
    def create(self, *, version: str) -> str: ...
    def restore(self, backup_id: str) -> None: ...


class MigrationRunner(Protocol):
    def migrate(self, *, migration_id: str, from_version: str, to_version: str) -> None: ...


class SecurityResponder(Protocol):
    def quarantine(self, *, version: str, reason: str) -> None: ...


@dataclass(frozen=True, slots=True)
class RolloutPolicy:
    canary_percent: int = 5
    stable_percent: int = 100
    health_checks: int = 3

    def validate(self) -> None:
        if not 1 <= self.canary_percent <= 100:
            raise ValueError("canary_percent must be between 1 and 100")
        if not 1 <= self.stable_percent <= 100:
            raise ValueError("stable_percent must be between 1 and 100")
        if self.health_checks < 1:
            raise ValueError("health_checks must be positive")


@dataclass(slots=True)
class ProductionReleaseController:
    updates: UpdateManager
    verifier: ReleaseVerifier
    health: HealthChecker
    backups: BackupStore
    migrations: MigrationRunner
    security: SecurityResponder
    policy: RolloutPolicy = field(default_factory=RolloutPolicy)
    state: ReleaseState = ReleaseState.VERIFIED
    active_channel: ReleaseChannel = ReleaseChannel.STABLE
    active_manifest: ReleaseManifest | None = None
    backup_id: str | None = None

    def deploy(self, manifest: ReleaseManifest, data: bytes) -> None:
        manifest.validate()
        self.policy.validate()
        if manifest.channel is ReleaseChannel.STABLE and self.active_channel is ReleaseChannel.STABLE:
            pass
        if not self.verifier.verify_signature(manifest, data):
            self.state = ReleaseState.FAILED
            raise ProductionReleaseError("release signature verification failed")
        if not self.verifier.verify_provenance(manifest):
            self.state = ReleaseState.FAILED
            raise ProductionReleaseError("release provenance verification failed")
        if not self.verifier.verify_sbom(manifest):
            self.state = ReleaseState.FAILED
            raise ProductionReleaseError("release SBOM verification failed")

        self.state = ReleaseState.STAGED
        self.updates.stage(manifest.artifact, data)
        self.backup_id = self.backups.create(version=self.updates.active_version)

        try:
            if manifest.migration_id is not None:
                self.migrations.migrate(
                    migration_id=manifest.migration_id,
                    from_version=self.updates.active_version,
                    to_version=manifest.artifact.version,
                )
            self.state = ReleaseState.ROLLING_OUT
            self.updates.apply(manifest.artifact.version)
            for _ in range(self.policy.health_checks):
                if not self.health.check(
                    version=manifest.artifact.version,
                    channel=manifest.channel,
                ):
                    raise ProductionReleaseError("post-deploy health check failed")
            self.active_manifest = manifest
            self.active_channel = manifest.channel
            self.state = ReleaseState.HEALTHY
        except Exception as exc:
            self._rollback(manifest.artifact.version, str(exc))
            raise

    def _rollback(self, version: str, reason: str) -> None:
        self.security.quarantine(version=version, reason=reason)
        try:
            if self.updates.previous_version is not None:
                self.updates.rollback()
            if self.backup_id is not None:
                self.backups.restore(self.backup_id)
        finally:
            self.state = ReleaseState.ROLLED_BACK
