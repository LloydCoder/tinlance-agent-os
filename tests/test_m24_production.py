from __future__ import annotations

import hashlib

import pytest

from tinlance_agent_os.distribution import ReleaseArtifact, UpdateManager
from tinlance_agent_os.production import (
    ProductionReleaseController,
    ProductionReleaseError,
    ReleaseChannel,
    ReleaseManifest,
    ReleaseState,
    RolloutPolicy,
    SBOMEvidence,
    SignatureEvidence,
    ProvenanceEvidence,
)


def artifact(version="2.0.0"):
    data = f"release-{version}".encode()
    return ReleaseArtifact(
        version,
        hashlib.sha256(data).hexdigest(),
        len(data),
        f"https://releases.example/{version}",
    ), data


class Verifier:
    def __init__(self, *, signature=True, provenance=True, sbom=True):
        self.signature = signature
        self.provenance = provenance
        self.sbom = sbom

    def verify_signature(self, manifest, data):
        return self.signature

    def verify_provenance(self, manifest):
        return self.provenance

    def verify_sbom(self, manifest):
        return self.sbom


class Health:
    def __init__(self, healthy=True):
        self.healthy = healthy

    def check(self, *, version, channel):
        return self.healthy


class Backups:
    def __init__(self):
        self.created = []
        self.restored = []

    def create(self, *, version):
        self.created.append(version)
        return f"backup-{version}"

    def restore(self, backup_id):
        self.restored.append(backup_id)


class Migrations:
    def __init__(self, fail=False):
        self.fail = fail
        self.calls = []

    def migrate(self, *, migration_id, from_version, to_version):
        self.calls.append((migration_id, from_version, to_version))
        if self.fail:
            raise RuntimeError("migration failure")


class Security:
    def __init__(self):
        self.quarantined = []

    def quarantine(self, *, version, reason):
        self.quarantined.append((version, reason))


def manifest(version="2.0.0"):
    release, _ = artifact(version)
    return ReleaseManifest(
        artifact=release,
        channel=ReleaseChannel.STABLE,
        signature=SignatureEvidence(
            bundle_uri="https://sigstore.example/bundle",
            signer_identity="release@tinlance.com",
            issuer="https://token.actions.githubusercontent.com",
        ),
        provenance=ProvenanceEvidence(
            predicate_type="https://slsa.dev/provenance/v1",
            source_repository="LloydCoder/tinlance-agent-os",
            source_revision="abc123",
            build_workflow=".github/workflows/release.yml",
        ),
        sbom=SBOMEvidence(
            format="cyclonedx",
            digest="a" * 64,
            uri="https://releases.example/sbom.json",
        ),
        migration_id="migration-2",
    )


def controller(*, verifier=None, health=None, migrations=None):
    return ProductionReleaseController(
        updates=UpdateManager(active_version="1.0.0"),
        verifier=verifier or Verifier(),
        health=health or Health(),
        backups=Backups(),
        migrations=migrations or Migrations(),
        security=Security(),
        policy=RolloutPolicy(health_checks=2),
    )


def test_release_requires_signature_provenance_and_sbom():
    release, data = artifact()
    for verifier in (
        Verifier(signature=False),
        Verifier(provenance=False),
        Verifier(sbom=False),
    ):
        ctl = controller(verifier=verifier)
        with pytest.raises(ProductionReleaseError):
            ctl.deploy(manifest(), data)
        assert ctl.state is ReleaseState.FAILED


def test_healthy_release_is_staged_migrated_and_activated():
    ctl = controller()
    release, data = artifact()
    ctl.deploy(manifest(), data)
    assert ctl.state is ReleaseState.HEALTHY
    assert ctl.updates.active_version == release.version
    assert ctl.active_manifest is not None
    assert ctl.backups.created == ["1.0.0"]


def test_health_failure_rolls_back_and_quarantines():
    security = Security()
    ctl = ProductionReleaseController(
        updates=UpdateManager(active_version="1.0.0"),
        verifier=Verifier(),
        health=Health(healthy=False),
        backups=Backups(),
        migrations=Migrations(),
        security=security,
    )
    release, data = artifact()
    with pytest.raises(ProductionReleaseError):
        ctl.deploy(manifest(), data)
    assert ctl.state is ReleaseState.ROLLED_BACK
    assert ctl.updates.active_version == "1.0.0"
    assert security.quarantined


def test_migration_failure_restores_backup():
    migrations = Migrations(fail=True)
    ctl = controller(migrations=migrations)
    _, data = artifact()
    with pytest.raises(RuntimeError, match="migration failure"):
        ctl.deploy(manifest(), data)
    assert ctl.state is ReleaseState.ROLLED_BACK
    assert ctl.updates.active_version == "1.0.0"
    assert ctl.backups.restored == ["backup-1.0.0"]


def test_manifest_validates_supply_chain_evidence_and_minimum_version():
    release, data = artifact()
    bad_sbom = manifest()
    bad_sbom = ReleaseManifest(
        artifact=release,
        channel=bad_sbom.channel,
        signature=bad_sbom.signature,
        provenance=bad_sbom.provenance,
        sbom=SBOMEvidence("cyclonedx", "not-a-digest", bad_sbom.sbom.uri),
    )
    with pytest.raises(ProductionReleaseError, match="SBOM digest"):
        controller().deploy(bad_sbom, data)

    incompatible = manifest()
    incompatible = ReleaseManifest(
        artifact=incompatible.artifact,
        channel=incompatible.channel,
        signature=incompatible.signature,
        provenance=incompatible.provenance,
        sbom=incompatible.sbom,
        minimum_version="1.5.0",
    )
    with pytest.raises(ProductionReleaseError, match="minimum_version"):
        controller().deploy(incompatible, data)


def test_backup_failure_clears_staged_release():
    class FailingBackups(Backups):
        def create(self, *, version):
            raise RuntimeError("backup unavailable")

    ctl = ProductionReleaseController(
        updates=UpdateManager(active_version="1.0.0"),
        verifier=Verifier(),
        health=Health(),
        backups=FailingBackups(),
        migrations=Migrations(),
        security=Security(),
    )
    _, data = artifact()
    with pytest.raises(ProductionReleaseError, match="backup"):
        ctl.deploy(manifest(), data)
    assert ctl.state is ReleaseState.FAILED
    assert ctl.updates.state.value == "idle"
    assert ctl.updates.staged_version is None


def test_migration_failure_does_not_attempt_unapplied_update_rollback():
    migrations = Migrations(fail=True)
    ctl = controller(migrations=migrations)
    _, data = artifact()
    with pytest.raises(RuntimeError, match="migration failure"):
        ctl.deploy(manifest(), data)
    assert ctl.updates.active_version == "1.0.0"
    assert ctl.updates.previous_version is None
    assert ctl.state is ReleaseState.ROLLED_BACK


def test_downgrade_is_rejected_before_deployment():
    ctl = controller()
    ctl.updates.active_version = "2.0.0"
    release, data = artifact("1.9.0")
    with pytest.raises(ValueError, match="downgrade"):
        ctl.deploy(manifest("1.9.0"), data)
