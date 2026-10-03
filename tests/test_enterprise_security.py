from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from tinlance_agent_os.enterprise_security import (
    AuditExport,
    DataPolicy,
    EnterpriseSecurityRuntime,
    KeyProvider,
    SecurityIncident,
    SecurityIntegration,
)
from tinlance_agent_os.store import StateStore


def make_runtime(tmp_path: Path) -> EnterpriseSecurityRuntime:
    return EnterpriseSecurityRuntime(StateStore(tmp_path / "state.db"))


def test_security_integrations_keys_exports_and_incidents(tmp_path: Path) -> None:
    runtime = make_runtime(tmp_path)
    runtime.register_identity(
        SecurityIntegration(
            "idp-1",
            "workspace-1",
            "oidc",
            "enterprise-idp",
            "configured",
            "https://idp.example",
        )
    )
    runtime.register_key_provider(KeyProvider("kms-1", "workspace-1", "hsm", "key-ref-1"))
    runtime.request_audit_export(
        AuditExport("export-1", "workspace-1", "s3://audit", "workspace", 86400)
    )
    policy = runtime.set_data_policy(DataPolicy("policy-1", "workspace-1", "eu", 86400, True, 3600))
    runtime.open_incident(SecurityIncident("incident-1", "workspace-1", "high", "export-1"))
    assert policy.generation == 0


def test_security_identity_and_retention_validation(tmp_path: Path) -> None:
    runtime = make_runtime(tmp_path)
    with pytest.raises(ValueError, match="provider"):
        runtime.register_key_provider(KeyProvider("kms-1", "workspace-1", "", "key"))
    with pytest.raises(ValueError, match="retention"):
        runtime.request_audit_export(AuditExport("export-1", "workspace-1", "dest", "scope", -1))
    with pytest.raises(ValueError, match="retention"):
        runtime.set_data_policy(DataPolicy("policy-1", "workspace-1", "eu", -1, False, 1))


def test_data_policy_revisions_and_unique_incidents(tmp_path: Path) -> None:
    runtime = make_runtime(tmp_path)
    first = runtime.set_data_policy(DataPolicy("policy-1", "workspace-1", "eu", 100, False, 10))
    second = runtime.set_data_policy(DataPolicy("policy-1", "workspace-1", "eu", 200, True, 20))
    assert first.generation == 0
    assert second.generation == 1
    incident = SecurityIncident("incident-1", "workspace-1", "medium")
    runtime.open_incident(incident)
    with pytest.raises(sqlite3.IntegrityError):
        runtime.open_incident(incident)
