from __future__ import annotations

from pathlib import Path

import pytest

from tinlance_agent_os.assurance import (
    EnterpriseGARuntime,
    GACompatibility,
    GACheck,
    GARelease,
)
from tinlance_agent_os.store import StateStore


def make_runtime(tmp_path: Path) -> EnterpriseGARuntime:
    return EnterpriseGARuntime(StateStore(tmp_path / "state.db"))


def test_ga_readiness_requires_all_non_waived_checks_to_pass(tmp_path: Path) -> None:
    runtime = make_runtime(tmp_path)
    runtime.register_release(GARelease("r1", "1.0.0", 1, "schema-1", "a" * 64, "sbom-1", "prov-1"))
    runtime.record_check(GACheck("ci-1", "r1", "ci", "CI", "passed", "run-1"))
    runtime.record_check(GACheck("security-1", "r1", "security", "security review", "pending"))
    assert runtime.readiness("r1").ready is False
    runtime.transition_check(
        "security-1", state="passed", evidence_ref="report-1", expected_generation=0
    )
    assert runtime.readiness("r1").ready is True


def test_completed_check_requires_evidence(tmp_path: Path) -> None:
    runtime = make_runtime(tmp_path)
    runtime.register_release(GARelease("r1", "1.0.0", 1, "schema-1", "a" * 64, "sbom-1", "prov-1"))
    with pytest.raises(ValueError, match="evidence_ref"):
        runtime.record_check(GACheck("ci-1", "r1", "ci", "CI", "passed"))


def test_compatibility_requires_known_release(tmp_path: Path) -> None:
    runtime = make_runtime(tmp_path)
    with pytest.raises(KeyError, match="unknown release"):
        runtime.register_compatibility(
            GACompatibility("c1", "r1", "agent-platform-api", "1.1", None, "supported")
        )
