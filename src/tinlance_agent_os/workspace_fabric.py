"""M27 enterprise workspace and organization fabric.

This module owns OS-level organizational context and configuration inheritance.
It does not authorize users or agents; Agent Platform remains authoritative for
identity, tenancy authorization, policy, approvals, and consequential execution.
"""

from __future__ import annotations

import json
import sqlite3
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path
from typing import Any


def _now() -> str:
    return datetime.now(UTC).isoformat()


class WorkspaceFabricError(RuntimeError):
    """Raised when organizational/workspace state is invalid."""


class EnvironmentKind(StrEnum):
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"


class WorkspaceState(StrEnum):
    ACTIVE = "active"
    ARCHIVED = "archived"
    DELETED = "deleted"


@dataclass(frozen=True, slots=True)
class Organization:
    organization_id: str
    name: str
    configuration: Mapping[str, object]


@dataclass(frozen=True, slots=True)
class Project:
    project_id: str
    organization_id: str
    name: str
    configuration: Mapping[str, object]


@dataclass(frozen=True, slots=True)
class Environment:
    environment_id: str
    project_id: str
    name: str
    kind: EnvironmentKind
    configuration: Mapping[str, object]


@dataclass(frozen=True, slots=True)
class WorkspaceProfile:
    workspace_id: str
    organization_id: str
    project_id: str
    environment_id: str
    state: WorkspaceState
    configuration: Mapping[str, object]
    generation: int


@dataclass(frozen=True, slots=True)
class WorkspaceTemplate:
    template_id: str
    organization_id: str
    name: str
    configuration: Mapping[str, object]
    generation: int


class WorkspaceFabric:
    """Durable organization/project/environment/workspace composition."""

    def __init__(self, path: Path) -> None:
        self.path = path
        self._ensure_schema()

    def create_organization(
        self,
        organization_id: str,
        name: str,
        configuration: Mapping[str, object] | None = None,
    ) -> Organization:
        self._require_text(organization_id, "organization_id")
        self._require_text(name, "name")
        config = self._json_object(configuration)
        now = _now()
        with self._db() as db:
            try:
                db.execute(
                    "INSERT INTO os_organizations VALUES (?,?,?,?)",
                    (organization_id, name, json.dumps(config, sort_keys=True), now),
                )
            except sqlite3.IntegrityError as exc:
                raise WorkspaceFabricError("organization already exists") from exc
        return Organization(organization_id, name, config)

    def create_project(
        self,
        project_id: str,
        organization_id: str,
        name: str,
        configuration: Mapping[str, object] | None = None,
    ) -> Project:
        self._require_text(project_id, "project_id")
        self._require_text(name, "name")
        config = self._json_object(configuration)
        with self._db() as db:
            if not self._exists(db, "os_organizations", "organization_id", organization_id):
                raise WorkspaceFabricError("organization does not exist")
            try:
                db.execute(
                    "INSERT INTO os_projects VALUES (?,?,?,?,?)",
                    (
                        project_id,
                        organization_id,
                        name,
                        json.dumps(config, sort_keys=True),
                        _now(),
                    ),
                )
            except sqlite3.IntegrityError as exc:
                raise WorkspaceFabricError("project already exists") from exc
        return Project(project_id, organization_id, name, config)

    def create_environment(
        self,
        environment_id: str,
        project_id: str,
        name: str,
        kind: EnvironmentKind,
        configuration: Mapping[str, object] | None = None,
    ) -> Environment:
        self._require_text(environment_id, "environment_id")
        self._require_text(name, "name")
        config = self._json_object(configuration)
        with self._db() as db:
            if not self._exists(db, "os_projects", "project_id", project_id):
                raise WorkspaceFabricError("project does not exist")
            try:
                db.execute(
                    "INSERT INTO os_environments VALUES (?,?,?,?,?,?)",
                    (
                        environment_id,
                        project_id,
                        name,
                        kind.value,
                        json.dumps(config, sort_keys=True),
                        _now(),
                    ),
                )
            except sqlite3.IntegrityError as exc:
                raise WorkspaceFabricError("environment already exists") from exc
        return Environment(environment_id, project_id, name, kind, config)

    def bind_workspace(
        self,
        workspace_id: str,
        organization_id: str,
        project_id: str,
        environment_id: str,
        configuration: Mapping[str, object] | None = None,
        *,
        expected_generation: int | None = None,
    ) -> WorkspaceProfile:
        config = self._json_object(configuration)
        with self._db() as db:
            if not self._exists(db, "workspaces", "workspace_id", workspace_id):
                raise WorkspaceFabricError("workspace does not exist")
            project = db.execute(
                "SELECT organization_id FROM os_projects WHERE project_id=?",
                (project_id,),
            ).fetchone()
            if project is None or project[0] != organization_id:
                raise WorkspaceFabricError("project is not owned by organization")
            environment = db.execute(
                "SELECT project_id FROM os_environments WHERE environment_id=?",
                (environment_id,),
            ).fetchone()
            if environment is None or environment[0] != project_id:
                raise WorkspaceFabricError("environment is not owned by project")
            row = db.execute(
                "SELECT generation FROM os_workspace_profiles WHERE workspace_id=?",
                (workspace_id,),
            ).fetchone()
            current = int(row[0]) if row else None
            if expected_generation is not None and current != expected_generation:
                raise WorkspaceFabricError("workspace generation conflict")
            generation = (current + 1) if current is not None else 1
            db.execute(
                """INSERT INTO os_workspace_profiles
                   VALUES (?,?,?,?,?,?,?,?)
                   ON CONFLICT(workspace_id) DO UPDATE SET
                     organization_id=excluded.organization_id,
                     project_id=excluded.project_id,
                     environment_id=excluded.environment_id,
                     state=excluded.state,
                     configuration=excluded.configuration,
                     generation=excluded.generation,
                     updated_at=excluded.updated_at""",
                (
                    workspace_id,
                    organization_id,
                    project_id,
                    environment_id,
                    WorkspaceState.ACTIVE.value,
                    json.dumps(config, sort_keys=True),
                    generation,
                    _now(),
                ),
            )
        return self.get_workspace(workspace_id)  # type: ignore[return-value]

    def get_workspace(self, workspace_id: str) -> WorkspaceProfile | None:
        with self._db() as db:
            row = db.execute(
                "SELECT * FROM os_workspace_profiles WHERE workspace_id=?",
                (workspace_id,),
            ).fetchone()
        if row is None:
            return None
        return WorkspaceProfile(
            row[0],
            row[1],
            row[2],
            row[3],
            WorkspaceState(row[4]),
            json.loads(row[5]),
            int(row[6]),
        )

    def effective_configuration(self, workspace_id: str) -> dict[str, object]:
        profile = self.get_workspace(workspace_id)
        if profile is None:
            raise WorkspaceFabricError("workspace profile does not exist")
        with self._db() as db:
            org = db.execute(
                "SELECT configuration FROM os_organizations WHERE organization_id=?",
                (profile.organization_id,),
            ).fetchone()
            project = db.execute(
                "SELECT configuration FROM os_projects WHERE project_id=?",
                (profile.project_id,),
            ).fetchone()
            environment = db.execute(
                "SELECT configuration FROM os_environments WHERE environment_id=?",
                (profile.environment_id,),
            ).fetchone()
        effective: dict[str, object] = {}
        for row in (org, project, environment):
            if row is not None:
                effective.update(json.loads(row[0]))
        effective.update(profile.configuration)
        return effective

    def create_template(
        self,
        template_id: str,
        organization_id: str,
        name: str,
        configuration: Mapping[str, object] | None = None,
    ) -> WorkspaceTemplate:
        self._require_text(template_id, "template_id")
        self._require_text(name, "name")
        config = self._json_object(configuration)
        with self._db() as db:
            if not self._exists(db, "os_organizations", "organization_id", organization_id):
                raise WorkspaceFabricError("organization does not exist")
            try:
                db.execute(
                    "INSERT INTO os_workspace_templates VALUES (?,?,?,?,?,?)",
                    (
                        template_id,
                        organization_id,
                        name,
                        json.dumps(config, sort_keys=True),
                        1,
                        _now(),
                    ),
                )
            except sqlite3.IntegrityError as exc:
                raise WorkspaceFabricError("workspace template already exists") from exc
        return WorkspaceTemplate(template_id, organization_id, name, config, 1)

    def archive_workspace(
        self,
        workspace_id: str,
        *,
        expected_generation: int | None = None,
    ) -> WorkspaceProfile:
        return self._set_state(workspace_id, WorkspaceState.ARCHIVED, expected_generation)

    def restore_workspace(
        self,
        workspace_id: str,
        *,
        expected_generation: int | None = None,
    ) -> WorkspaceProfile:
        return self._set_state(workspace_id, WorkspaceState.ACTIVE, expected_generation)

    def export_workspace(self, workspace_id: str) -> dict[str, object]:
        profile = self.get_workspace(workspace_id)
        if profile is None:
            raise WorkspaceFabricError("workspace profile does not exist")
        return {
            "workspace": {
                "workspace_id": profile.workspace_id,
                "organization_id": profile.organization_id,
                "project_id": profile.project_id,
                "environment_id": profile.environment_id,
                "state": profile.state.value,
                "configuration": dict(profile.configuration),
                "generation": profile.generation,
            },
            "effective_configuration": self.effective_configuration(workspace_id),
        }

    def _set_state(
        self,
        workspace_id: str,
        state: WorkspaceState,
        expected_generation: int | None,
    ) -> WorkspaceProfile:
        with self._db() as db:
            row = db.execute(
                "SELECT generation FROM os_workspace_profiles WHERE workspace_id=?",
                (workspace_id,),
            ).fetchone()
            if row is None:
                raise WorkspaceFabricError("workspace profile does not exist")
            current = int(row[0])
            if expected_generation is not None and current != expected_generation:
                raise WorkspaceFabricError("workspace generation conflict")
            generation = current + 1
            db.execute(
                "UPDATE os_workspace_profiles SET state=?,generation=?,updated_at=? "
                "WHERE workspace_id=? AND generation=?",
                (state.value, generation, _now(), workspace_id, current),
            )
        return self.get_workspace(workspace_id)  # type: ignore[return-value]

    def _ensure_schema(self) -> None:
        with self._db() as db:
            db.executescript(
                """
                CREATE TABLE IF NOT EXISTS os_organizations (
                    organization_id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    configuration TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS os_projects (
                    project_id TEXT PRIMARY KEY,
                    organization_id TEXT NOT NULL
                        REFERENCES os_organizations(organization_id),
                    name TEXT NOT NULL,
                    configuration TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS os_environments (
                    environment_id TEXT PRIMARY KEY,
                    project_id TEXT NOT NULL REFERENCES os_projects(project_id),
                    name TEXT NOT NULL,
                    kind TEXT NOT NULL,
                    configuration TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS os_workspace_profiles (
                    workspace_id TEXT PRIMARY KEY REFERENCES workspaces(workspace_id),
                    organization_id TEXT NOT NULL
                        REFERENCES os_organizations(organization_id),
                    project_id TEXT NOT NULL REFERENCES os_projects(project_id),
                    environment_id TEXT NOT NULL REFERENCES os_environments(environment_id),
                    state TEXT NOT NULL,
                    configuration TEXT NOT NULL,
                    generation INTEGER NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS os_workspace_templates (
                    template_id TEXT PRIMARY KEY,
                    organization_id TEXT NOT NULL
                        REFERENCES os_organizations(organization_id),
                    name TEXT NOT NULL,
                    configuration TEXT NOT NULL,
                    generation INTEGER NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_os_projects_org
                    ON os_projects(organization_id);
                CREATE INDEX IF NOT EXISTS idx_os_environments_project
                    ON os_environments(project_id);
                CREATE INDEX IF NOT EXISTS idx_os_workspace_org
                    ON os_workspace_profiles(organization_id, project_id, environment_id);
                """
            )

    def _db(self) -> sqlite3.Connection:
        db = sqlite3.connect(self.path)
        db.execute("PRAGMA foreign_keys=ON")
        return db

    @staticmethod
    def _exists(
        db: sqlite3.Connection,
        table: str,
        column: str,
        value: str,
    ) -> bool:
        row = db.execute(
            f"SELECT 1 FROM {table} WHERE {column}=?",
            (value,),
        ).fetchone()
        return row is not None

    @staticmethod
    def _json_object(value: Mapping[str, object] | None) -> dict[str, object]:
        result = dict(value or {})
        try:
            json.dumps(result, sort_keys=True)
        except (TypeError, ValueError) as exc:
            raise WorkspaceFabricError("configuration must be JSON serializable") from exc
        return result

    @staticmethod
    def _require_text(value: str, name: str) -> None:
        if not value.strip():
            raise WorkspaceFabricError(f"{name} is required")
