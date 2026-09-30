"""M18 package/runtime boundary for skills, applications, extensions and connectors."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Protocol


class PackageType(StrEnum):
    SKILL = "skill"
    APPLICATION = "application"
    EXTENSION = "extension"
    CONNECTOR = "connector"
    AGENT = "agent"


class PackageState(StrEnum):
    VERIFIED = "verified"
    ENABLED = "enabled"
    QUARANTINED = "quarantined"
    ROLLED_BACK = "rolled_back"
    REMOVED = "removed"


class PackageError(RuntimeError):
    pass


class PackageSignatureVerifier(Protocol):
    def verify(self, *, digest: str, signature: str, signer: str) -> bool: ...


@dataclass(frozen=True, slots=True)
class PackageDependency:
    package_id: str
    version: str


@dataclass(frozen=True, slots=True)
class PackageManifest:
    package_id: str
    package_type: PackageType
    version: str
    artifact_sha256: str
    signer: str
    signature: str
    capabilities: frozenset[str] = frozenset()
    dependencies: tuple[PackageDependency, ...] = ()
    provenance: str = ""

    def validate(self) -> None:
        if not all(
            value.strip()
            for value in (
                self.package_id,
                self.version,
                self.artifact_sha256,
                self.signer,
                self.signature,
                self.provenance,
            )
        ):
            raise PackageError("package manifest is incomplete")
        digest = self.artifact_sha256.lower()
        if len(digest) != 64 or any(c not in "0123456789abcdef" for c in digest):
            raise PackageError("artifact_sha256 must be a SHA-256 digest")
        if len(self.capabilities) != len(set(self.capabilities)):
            raise PackageError("duplicate capability requirement")
        if any(not dependency.package_id.strip() for dependency in self.dependencies):
            raise PackageError("invalid package dependency")


@dataclass(frozen=True, slots=True)
class CapabilityGrant:
    package_id: str
    capability_id: str
    grant_id: str
    platform_authorized: bool


@dataclass(slots=True)
class PackageRecord:
    manifest: PackageManifest
    state: PackageState
    artifact: bytes
    previous_version: str | None = None
    grants: set[str] = field(default_factory=set)


class AgentEcosystemRuntime:
    def __init__(self, verifier: PackageSignatureVerifier) -> None:
        self.verifier = verifier
        self.packages: dict[tuple[str, str], PackageRecord] = {}
        self.active: dict[str, str] = {}

    def install(self, manifest: PackageManifest, artifact: bytes) -> None:
        manifest.validate()
        digest = hashlib.sha256(artifact).hexdigest()
        if digest != manifest.artifact_sha256.lower():
            raise PackageError("artifact hash mismatch")
        if not self.verifier.verify(
            digest=digest, signature=manifest.signature, signer=manifest.signer
        ):
            raise PackageError("package signature verification failed")
        current_version = self.active.get(manifest.package_id)
        if current_version == manifest.version:
            return
        previous = current_version
        self.packages[(manifest.package_id, manifest.version)] = PackageRecord(
            manifest=manifest,
            state=PackageState.VERIFIED,
            artifact=artifact,
            previous_version=previous,
        )
        self.active[manifest.package_id] = manifest.version

    def resolve(self, package_id: str) -> tuple[PackageManifest, ...]:
        active_version = self.active.get(package_id)
        if active_version is None or (package_id, active_version) not in self.packages:
            raise PackageError("package not installed")
        ordered: list[PackageManifest] = []
        visiting: set[str] = set()
        visited: set[str] = set()

        def visit(current_id: str) -> None:
            if current_id in visiting:
                raise PackageError("package dependency cycle")
            if current_id in visited:
                return
            active_version = self.active.get(current_id)
            record = self.packages.get((current_id, active_version)) if active_version else None
            if record is None:
                raise PackageError("package dependency is not installed")
            visiting.add(current_id)
            for dependency in record.manifest.dependencies:
                dependency_record = self.packages.get((dependency.package_id, dependency.version))
                if dependency_record is None:
                    raise PackageError("package dependency version mismatch")
                visit(dependency.package_id)
            visiting.remove(current_id)
            visited.add(current_id)
            ordered.append(record.manifest)

        visit(package_id)
        return tuple(ordered)

    def enable(self, package_id: str) -> None:
        active_version = self.active.get(package_id)
        record = self.packages[(package_id, active_version)] if active_version else None
        if record is None:
            raise PackageError("package is not installed")
        self.resolve(package_id)
        if record.state is PackageState.QUARANTINED:
            raise PackageError("quarantined package cannot be enabled")
        record.state = PackageState.ENABLED
        self.active[package_id] = record.manifest.version

    def quarantine(self, package_id: str) -> None:
        active_version = self.active.get(package_id)
        if active_version is None:
            raise PackageError("package is not installed")
        self.packages[(package_id, active_version)].state = PackageState.QUARANTINED

    def rollback(self, package_id: str) -> None:
        active_version = self.active.get(package_id)
        record = self.packages.get((package_id, active_version)) if active_version else None
        if record is None or record.previous_version is None:
            raise PackageError("no previous package version")
        previous = self.packages.get((package_id, record.previous_version))
        if previous is None:
            raise PackageError("previous package artifact is unavailable")
        record.state = PackageState.ROLLED_BACK
        previous.state = PackageState.ENABLED
        self.active[package_id] = previous.manifest.version

    def apply_platform_grant(self, grant: CapabilityGrant) -> None:
        active_version = self.active.get(grant.package_id)
        record = self.packages.get((grant.package_id, active_version)) if active_version else None
        if record is None:
            raise PackageError("package is not installed")
        if grant.capability_id not in record.manifest.capabilities:
            raise PackageError("grant exceeds manifest capability request")
        if not grant.platform_authorized:
            raise PackageError("Platform did not authorize capability grant")
        record.grants.add(grant.grant_id)
