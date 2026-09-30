from __future__ import annotations

import hashlib
from dataclasses import replace

import pytest

from tinlance_agent_os.ecosystem import (
    AgentEcosystemRuntime,
    CapabilityGrant,
    PackageDependency,
    PackageError,
    PackageManifest,
    PackageState,
    PackageType,
)


class Verifier:
    def verify(self, *, digest, signature, signer):
        return signature == f"{signer}:{digest}"


def manifest(package_id="pkg", version="1.0.0", deps=(), caps=frozenset({"read"})):
    artifact = f"{package_id}-{version}".encode()
    digest = hashlib.sha256(artifact).hexdigest()
    return (
        PackageManifest(
            package_id=package_id,
            package_type=PackageType.EXTENSION,
            version=version,
            artifact_sha256=digest,
            signer="trusted",
            signature=f"trusted:{digest}",
            capabilities=caps,
            dependencies=deps,
            provenance="build-attestation",
        ),
        artifact,
    )


def test_install_requires_hash_and_signature():
    runtime = AgentEcosystemRuntime(Verifier())
    package, artifact = manifest()
    runtime.install(package, artifact)
    runtime.enable(package.package_id)
    assert runtime.packages[(package.package_id, package.version)].state is PackageState.ENABLED


def test_tampered_artifact_is_rejected():
    runtime = AgentEcosystemRuntime(Verifier())
    package, _ = manifest()
    with pytest.raises(PackageError, match="hash"):
        runtime.install(package, b"tampered")


def test_untrusted_signature_is_rejected():
    runtime = AgentEcosystemRuntime(Verifier())
    package, artifact = manifest()
    bad = replace(package, signature="bad")
    with pytest.raises(PackageError):
        runtime.install(bad, artifact)


def test_dependency_resolution_is_topological():
    runtime = AgentEcosystemRuntime(Verifier())
    base, base_artifact = manifest("base", "1.0.0")
    app, app_artifact = manifest(
        "app", "1.0.0", (PackageDependency("base", "1.0.0"),)
    )
    runtime.install(base, base_artifact)
    runtime.install(app, app_artifact)
    assert [item.package_id for item in runtime.resolve("app")] == ["base", "app"]


def test_dependency_version_confusion_is_rejected():
    runtime = AgentEcosystemRuntime(Verifier())
    base, base_artifact = manifest("base", "1.1.0")
    app, app_artifact = manifest(
        "app", "1.0.0", (PackageDependency("base", "1.0.0"),)
    )
    runtime.install(base, base_artifact)
    runtime.install(app, app_artifact)
    with pytest.raises(PackageError, match="version"):
        runtime.enable("app")


def test_manifest_cannot_self_grant_capability():
    runtime = AgentEcosystemRuntime(Verifier())
    package, artifact = manifest(caps=frozenset({"read"}))
    runtime.install(package, artifact)
    runtime.enable(package.package_id)
    with pytest.raises(PackageError, match="exceeds"):
        runtime.apply_platform_grant(
            CapabilityGrant(package.package_id, "admin", "grant-1", True)
        )


def test_platform_authorization_is_required():
    runtime = AgentEcosystemRuntime(Verifier())
    package, artifact = manifest()
    runtime.install(package, artifact)
    runtime.enable(package.package_id)
    with pytest.raises(PackageError, match="Platform"):
        runtime.apply_platform_grant(
            CapabilityGrant(package.package_id, "read", "grant-1", False)
        )


def test_rollback_uses_verified_previous_artifact():
    runtime = AgentEcosystemRuntime(Verifier())
    first, first_artifact = manifest("pkg", "1.0.0")
    second, second_artifact = manifest("pkg", "2.0.0")
    runtime.install(first, first_artifact)
    runtime.enable("pkg")
    runtime.install(second, second_artifact)
    runtime.enable("pkg")
    runtime.rollback("pkg")
    assert runtime.active["pkg"] == "1.0.0"


def test_quarantine_blocks_enablement():
    runtime = AgentEcosystemRuntime(Verifier())
    package, artifact = manifest()
    runtime.install(package, artifact)
    runtime.quarantine(package.package_id)
    with pytest.raises(PackageError, match="quarantined"):
        runtime.enable(package.package_id)
