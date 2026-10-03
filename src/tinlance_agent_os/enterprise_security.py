"""Enterprise security and compliance integration contracts.

M39 models enterprise identity-provider, key-management, audit-export, data
residency/retention and incident-response integration state. These records
describe external controls; they do not replace Agent Platform authorization.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from typing import Final, Literal

from .store import StateStore

IdentityProtocol = Literal["oidc", "saml", "scim"]
IntegrationState = Literal["configured", "degraded", "disabled"]
ExportState = Literal["requested", "running", "completed", "failed"]

_SCHEMA: Final = """
CREATE TABLE IF NOT EXISTS security_integrations (
    integration_id TEXT PRIMARY KEY,
    workspace_id TEXT NOT NULL,
    protocol TEXT NOT NULL CHECK(protocol IN ('oidc','saml','scim')),
    provider TEXT NOT NULL,
    state TEXT NOT NULL CHECK(state IN ('configured','degraded','disabled')),
    endpoint_ref TEXT NOT NULL,
    generation INTEGER NOT NULL CHECK(generation >= 0)
);

CREATE TABLE IF NOT EXISTS key_providers (
    provider_id TEXT PRIMARY KEY,
    workspace_id TEXT NOT NULL,
    provider TEXT NOT NULL,
    key_ref TEXT NOT NULL,
    state TEXT NOT NULL CHECK(state IN ('configured','degraded','disabled')),
    generation INTEGER NOT NULL CHECK(generation >= 0)
);

CREATE TABLE IF NOT EXISTS audit_exports (
    export_id TEXT PRIMARY KEY,
    workspace_id TEXT NOT NULL,
    destination_ref TEXT NOT NULL,
    scope_ref TEXT NOT NULL,
    retention_seconds INTEGER NOT NULL CHECK(retention_seconds >= 0),
    state TEXT NOT NULL CHECK(state IN ('requested','running','completed','failed')),
    generation INTEGER NOT NULL CHECK(generation >= 0)
);

CREATE TABLE IF NOT EXISTS data_policies (
    policy_id TEXT PRIMARY KEY,
    workspace_id TEXT NOT NULL,
    residency_region TEXT NOT NULL,
    retention_seconds INTEGER NOT NULL CHECK(retention_seconds >= 0),
    legal_hold INTEGER NOT NULL CHECK(legal_hold IN (0,1)),
    deletion_window_seconds INTEGER NOT NULL CHECK(deletion_window_seconds >= 0),
    generation INTEGER NOT NULL CHECK(generation >= 0)
);

CREATE TABLE IF NOT EXISTS security_incidents (
    incident_id TEXT PRIMARY KEY,
    workspace_id TEXT NOT NULL,
    severity TEXT NOT NULL,
    evidence_export_ref TEXT,
    state TEXT NOT NULL,
    generation INTEGER NOT NULL CHECK(generation >= 0)
);
"""


@dataclass(frozen=True, slots=True)
class SecurityIntegration:
    integration_id: str
    workspace_id: str
    protocol: IdentityProtocol
    provider: str
    state: IntegrationState
    endpoint_ref: str
    generation: int = 0


@dataclass(frozen=True, slots=True)
class KeyProvider:
    provider_id: str
    workspace_id: str
    provider: str
    key_ref: str
    state: IntegrationState = "configured"
    generation: int = 0


@dataclass(frozen=True, slots=True)
class AuditExport:
    export_id: str
    workspace_id: str
    destination_ref: str
    scope_ref: str
    retention_seconds: int
    state: ExportState = "requested"
    generation: int = 0


@dataclass(frozen=True, slots=True)
class DataPolicy:
    policy_id: str
    workspace_id: str
    residency_region: str
    retention_seconds: int
    legal_hold: bool
    deletion_window_seconds: int
    generation: int = 0


@dataclass(frozen=True, slots=True)
class SecurityIncident:
    incident_id: str
    workspace_id: str
    severity: str
    evidence_export_ref: str | None = None
    state: str = "open"
    generation: int = 0


class EnterpriseSecurityRuntime:
    """Durable enterprise security/compliance integration metadata."""

    def __init__(self, store: StateStore) -> None:
        self.store = store
        with sqlite3.connect(store.path) as db:
            db.executescript(_SCHEMA)

    @staticmethod
    def _identity(value: str, label: str) -> None:
        if not value:
            raise ValueError(f"{label} is required")

    def register_identity(self, integration: SecurityIntegration) -> SecurityIntegration:
        self._identity(integration.integration_id, "integration_id")
        self._identity(integration.workspace_id, "workspace_id")
        self._identity(integration.provider, "provider")
        self._identity(integration.endpoint_ref, "endpoint_ref")
        with sqlite3.connect(self.store.path) as db:
            db.execute(
                """INSERT INTO security_integrations
                (integration_id,workspace_id,protocol,provider,state,endpoint_ref,generation)
                VALUES (?,?,?,?,?,?,?)""",
                (
                    integration.integration_id,
                    integration.workspace_id,
                    integration.protocol,
                    integration.provider,
                    integration.state,
                    integration.endpoint_ref,
                    integration.generation,
                ),
            )
        return integration

    def register_key_provider(self, provider: KeyProvider) -> KeyProvider:
        self._identity(provider.provider_id, "provider_id")
        self._identity(provider.workspace_id, "workspace_id")
        self._identity(provider.provider, "provider")
        self._identity(provider.key_ref, "key_ref")
        with sqlite3.connect(self.store.path) as db:
            db.execute(
                """INSERT INTO key_providers
                (provider_id,workspace_id,provider,key_ref,state,generation)
                VALUES (?,?,?,?,?,?)""",
                (
                    provider.provider_id,
                    provider.workspace_id,
                    provider.provider,
                    provider.key_ref,
                    provider.state,
                    provider.generation,
                ),
            )
        return provider

    def request_audit_export(self, export: AuditExport) -> AuditExport:
        self._identity(export.export_id, "export_id")
        self._identity(export.workspace_id, "workspace_id")
        self._identity(export.destination_ref, "destination_ref")
        self._identity(export.scope_ref, "scope_ref")
        if export.retention_seconds < 0:
            raise ValueError("retention_seconds must be non-negative")
        with sqlite3.connect(self.store.path) as db:
            db.execute(
                """INSERT INTO audit_exports
                (export_id,workspace_id,destination_ref,scope_ref,retention_seconds,state,generation)
                VALUES (?,?,?,?,?,?,?)""",
                (
                    export.export_id,
                    export.workspace_id,
                    export.destination_ref,
                    export.scope_ref,
                    export.retention_seconds,
                    export.state,
                    export.generation,
                ),
            )
        return export

    def set_data_policy(self, policy: DataPolicy) -> DataPolicy:
        self._identity(policy.policy_id, "policy_id")
        self._identity(policy.workspace_id, "workspace_id")
        self._identity(policy.residency_region, "residency_region")
        if policy.retention_seconds < 0 or policy.deletion_window_seconds < 0:
            raise ValueError("retention and deletion windows must be non-negative")
        with sqlite3.connect(self.store.path) as db:
            current = db.execute(
                "SELECT generation FROM data_policies WHERE policy_id=?",
                (policy.policy_id,),
            ).fetchone()
            generation = policy.generation if current is None else int(current[0]) + 1
            db.execute(
                """INSERT INTO data_policies
                (policy_id,workspace_id,residency_region,retention_seconds,legal_hold,
                 deletion_window_seconds,generation)
                VALUES (?,?,?,?,?,?,?)
                ON CONFLICT(policy_id) DO UPDATE SET
                  workspace_id=excluded.workspace_id,
                  residency_region=excluded.residency_region,
                  retention_seconds=excluded.retention_seconds,
                  legal_hold=excluded.legal_hold,
                  deletion_window_seconds=excluded.deletion_window_seconds,
                  generation=excluded.generation""",
                (
                    policy.policy_id,
                    policy.workspace_id,
                    policy.residency_region,
                    policy.retention_seconds,
                    int(policy.legal_hold),
                    policy.deletion_window_seconds,
                    generation,
                ),
            )
        return DataPolicy(
            policy.policy_id,
            policy.workspace_id,
            policy.residency_region,
            policy.retention_seconds,
            policy.legal_hold,
            policy.deletion_window_seconds,
            generation,
        )

    def open_incident(self, incident: SecurityIncident) -> SecurityIncident:
        self._identity(incident.incident_id, "incident_id")
        self._identity(incident.workspace_id, "workspace_id")
        self._identity(incident.severity, "severity")
        with sqlite3.connect(self.store.path) as db:
            db.execute(
                """INSERT INTO security_incidents
                (incident_id,workspace_id,severity,evidence_export_ref,state,generation)
                VALUES (?,?,?,?,?,?)""",
                (
                    incident.incident_id,
                    incident.workspace_id,
                    incident.severity,
                    incident.evidence_export_ref,
                    incident.state,
                    incident.generation,
                ),
            )
        return incident
