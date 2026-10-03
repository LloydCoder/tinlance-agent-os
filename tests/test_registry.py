from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from tinlance_agent_os.registry import (
    AgentRegistry,
    RegistryPackage,
    RegistryPublisher,
    RegistryVersion,
)
from tinlance_agent_os.store import StateStore


def make_registry(tmp_path: Path) -> AgentRegistry:
    return AgentRegistry(StateStore(tmp_path / "state.db"))


def test_registry_publisher_package_and_signed_version(tmp_path: Path) -> None:
    registry = make_registry(tmp_path)
    registry.register_publisher(RegistryPublisher("pub-1", "Tinlance", "oidc:tinlance", "trusted"))
    registry.register_package(RegistryPackage("pkg-1", "pub-1", "research-agent", "agent"))
    version = registry.register_version(
        RegistryVersion(
            "pkg-1",
            "1.0.0",
            "a" * 64,
            "sig-1",
            "prov-1",
            "sbom-1",
            "agent-os>=0.1",
        )
    )
    assert version.version == "1.0.0"


def test_registry_rejects_unsigned_published_version_and_bad_digest(tmp_path: Path) -> None:
    registry = make_registry(tmp_path)
    registry.register_publisher(RegistryPublisher("pub-1", "Tinlance", "identity", "trusted"))
    registry.register_package(RegistryPackage("pkg-1", "pub-1", "agent", "agent"))
    with pytest.raises(ValueError, match="signature"):
        registry.register_version(
            RegistryVersion("pkg-1", "1.0.0", "b" * 64, None, None, None, ">=0.1")
        )
    with pytest.raises(ValueError, match="SHA-256"):
        registry.register_version(
            RegistryVersion("pkg-1", "1.0.1", "bad", "sig", None, None, ">=0.1")
        )


def test_blocked_publisher_and_generation_fail_closed(tmp_path: Path) -> None:
    registry = make_registry(tmp_path)
    registry.register_publisher(RegistryPublisher("pub-1", "Blocked", "identity", "blocked"))
    with pytest.raises(ValueError, match="blocked"):
        registry.register_package(RegistryPackage("pkg-1", "pub-1", "agent", "agent"))

    registry.register_publisher(RegistryPublisher("pub-2", "Trusted", "identity", "trusted"))
    registry.register_package(RegistryPackage("pkg-2", "pub-2", "agent", "agent"))
    registry.register_version(
        RegistryVersion("pkg-2", "1.0.0", "c" * 64, "sig", "prov", "sbom", ">=0.1")
    )
    with pytest.raises(ValueError, match="generation"):
        registry.set_version_state("pkg-2", "1.0.0", "quarantined", expected_generation=1)


def test_duplicate_version_ids_are_rejected(tmp_path: Path) -> None:
    registry = make_registry(tmp_path)
    registry.register_publisher(RegistryPublisher("pub-1", "Tinlance", "identity", "trusted"))
    registry.register_package(RegistryPackage("pkg-1", "pub-1", "agent", "agent"))
    version = RegistryVersion("pkg-1", "1.0.0", "d" * 64, "sig", "prov", "sbom", ">=0.1")
    registry.register_version(version)
    with pytest.raises(sqlite3.IntegrityError):
        registry.register_version(version)
