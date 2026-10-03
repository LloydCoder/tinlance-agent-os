"""Agent marketplace and enterprise registry contracts.

M36 models publisher identity metadata, package versions, provenance/SBOM
references, compatibility, trust state, quarantine and revocation. It never
executes packages or grants capabilities; Platform remains authoritative.
"""

from __future__ import annotations

import re
import sqlite3
from dataclasses import dataclass
from typing import Final, Literal

from .store import StateStore

PackageState = Literal["published", "quarantined", "revoked", "deprecated"]
TrustState = Literal["trusted", "untrusted", "blocked"]

_SCHEMA: Final = """
CREATE TABLE IF NOT EXISTS registry_publishers (
    publisher_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    identity_ref TEXT NOT NULL,
    trust_state TEXT NOT NULL CHECK(trust_state IN ('trusted','untrusted','blocked')),
    generation INTEGER NOT NULL CHECK(generation >= 0)
);

CREATE TABLE IF NOT EXISTS registry_packages (
    package_id TEXT PRIMARY KEY,
    publisher_id TEXT NOT NULL REFERENCES registry_publishers(publisher_id),
    name TEXT NOT NULL,
    package_type TEXT NOT NULL,
    state TEXT NOT NULL CHECK(state IN ('published','quarantined','revoked','deprecated')),
    generation INTEGER NOT NULL CHECK(generation >= 0),
    UNIQUE(publisher_id, name)
);

CREATE TABLE IF NOT EXISTS registry_versions (
    package_id TEXT NOT NULL REFERENCES registry_packages(package_id),
    version TEXT NOT NULL,
    artifact_digest TEXT NOT NULL,
    signature_ref TEXT,
    provenance_ref TEXT,
    sbom_ref TEXT,
    compatibility TEXT NOT NULL,
    state TEXT NOT NULL CHECK(state IN ('published','quarantined','revoked','deprecated')),
    generation INTEGER NOT NULL CHECK(generation >= 0),
    PRIMARY KEY(package_id, version)
);
CREATE INDEX IF NOT EXISTS idx_registry_versions_digest
    ON registry_versions(artifact_digest);
"""


@dataclass(frozen=True, slots=True)
class RegistryPublisher:
    publisher_id: str
    name: str
    identity_ref: str
    trust_state: TrustState = "untrusted"
    generation: int = 0


@dataclass(frozen=True, slots=True)
class RegistryPackage:
    package_id: str
    publisher_id: str
    name: str
    package_type: str
    state: PackageState = "published"
    generation: int = 0


@dataclass(frozen=True, slots=True)
class RegistryVersion:
    package_id: str
    version: str
    artifact_digest: str
    signature_ref: str | None
    provenance_ref: str | None
    sbom_ref: str | None
    compatibility: str
    state: PackageState = "published"
    generation: int = 0


class AgentRegistry:
    """Durable package registry metadata and supply-chain state."""

    def __init__(self, store: StateStore) -> None:
        self.store = store
        with sqlite3.connect(store.path) as db:
            db.executescript(_SCHEMA)

    @staticmethod
    def _digest(value: str) -> None:
        if not re.fullmatch(r"[0-9a-f]{64}", value):
            raise ValueError("artifact_digest must be a lowercase SHA-256 hex digest")

    def register_publisher(self, publisher: RegistryPublisher) -> RegistryPublisher:
        if not publisher.publisher_id or not publisher.name or not publisher.identity_ref:
            raise ValueError("publisher identity is required")
        with sqlite3.connect(self.store.path) as db:
            db.execute(
                """INSERT INTO registry_publishers
                (publisher_id,name,identity_ref,trust_state,generation)
                VALUES (?,?,?,?,?)""",
                (
                    publisher.publisher_id,
                    publisher.name,
                    publisher.identity_ref,
                    publisher.trust_state,
                    publisher.generation,
                ),
            )
        return publisher

    def register_package(self, package: RegistryPackage) -> RegistryPackage:
        if not package.package_id or not package.publisher_id or not package.name:
            raise ValueError("package identity is required")
        with sqlite3.connect(self.store.path) as db:
            publisher = db.execute(
                "SELECT trust_state FROM registry_publishers WHERE publisher_id=?",
                (package.publisher_id,),
            ).fetchone()
            if publisher is None:
                raise KeyError(f"unknown publisher: {package.publisher_id}")
            if str(publisher[0]) == "blocked":
                raise ValueError("blocked publisher cannot register packages")
            db.execute(
                """INSERT INTO registry_packages
                (package_id,publisher_id,name,package_type,state,generation)
                VALUES (?,?,?,?,?,?)""",
                (
                    package.package_id,
                    package.publisher_id,
                    package.name,
                    package.package_type,
                    package.state,
                    package.generation,
                ),
            )
        return package

    def register_version(self, version: RegistryVersion) -> RegistryVersion:
        if not version.package_id or not version.version or not version.compatibility:
            raise ValueError("version identity is required")
        self._digest(version.artifact_digest)
        if version.state == "published" and not version.signature_ref:
            raise ValueError("published versions require a signature reference")
        with sqlite3.connect(self.store.path) as db:
            package = db.execute(
                "SELECT publisher_id,state FROM registry_packages WHERE package_id=?",
                (version.package_id,),
            ).fetchone()
            if package is None:
                raise KeyError(f"unknown package: {version.package_id}")
            publisher = db.execute(
                "SELECT trust_state FROM registry_publishers WHERE publisher_id=?",
                (package[0],),
            ).fetchone()
            if publisher is None or str(publisher[0]) == "blocked":
                raise ValueError("package publisher is blocked")
            db.execute(
                """INSERT INTO registry_versions
                (package_id,version,artifact_digest,signature_ref,provenance_ref,sbom_ref,
                 compatibility,state,generation)
                VALUES (?,?,?,?,?,?,?,?,?)""",
                (
                    version.package_id,
                    version.version,
                    version.artifact_digest,
                    version.signature_ref,
                    version.provenance_ref,
                    version.sbom_ref,
                    version.compatibility,
                    version.state,
                    version.generation,
                ),
            )
        return version

    def set_version_state(
        self,
        package_id: str,
        version: str,
        state: PackageState,
        *,
        expected_generation: int,
    ) -> RegistryVersion:
        with sqlite3.connect(self.store.path) as db:
            row = db.execute(
                """SELECT package_id,version,artifact_digest,signature_ref,provenance_ref,
                          sbom_ref,compatibility,state,generation
                   FROM registry_versions WHERE package_id=? AND version=?""",
                (package_id, version),
            ).fetchone()
            if row is None:
                raise KeyError("unknown package version")
            if int(row[8]) != expected_generation:
                raise ValueError(
                    f"generation conflict: expected {expected_generation}, actual {row[8]}"
                )
            next_generation = int(row[8]) + 1
            db.execute(
                "UPDATE registry_versions SET state=?,generation=? "
                "WHERE package_id=? AND version=?",
                (state, next_generation, package_id, version),
            )
        return RegistryVersion(
            str(row[0]),
            str(row[1]),
            str(row[2]),
            row[3],
            row[4],
            row[5],
            str(row[6]),
            state,
            next_generation,
        )
