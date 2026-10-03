from pathlib import Path

import pytest

from tinlance_agent_os.store import StateStore
from tinlance_agent_os.workspace_fabric import (
    EnvironmentKind,
    WorkspaceFabric,
    WorkspaceFabricError,
    WorkspaceState,
)


def fabric(tmp_path: Path) -> tuple[StateStore, WorkspaceFabric]:
    store = StateStore(tmp_path / "state.db")
    return store, WorkspaceFabric(store.path)


def setup_hierarchy(fabric: WorkspaceFabric, store: StateStore) -> None:
    store.upsert_workspace("ws-1", "user-1", "2026-01-01T00:00:00+00:00")
    fabric.create_organization("org-1", "Tinlance", {"region": "eu"})
    fabric.create_project("project-1", "org-1", "Platform", {"tier": "core"})
    fabric.create_environment(
        "env-1",
        "project-1",
        "Production",
        EnvironmentKind.PRODUCTION,
        {"region": "de"},
    )


def test_hierarchy_and_effective_configuration(tmp_path: Path) -> None:
    store, wf = fabric(tmp_path)
    setup_hierarchy(wf, store)

    profile = wf.bind_workspace(
        "ws-1",
        "org-1",
        "project-1",
        "env-1",
        {"region": "workspace", "feature": "enabled"},
    )

    assert profile.generation == 1
    assert wf.effective_configuration("ws-1") == {
        "region": "workspace",
        "tier": "core",
        "feature": "enabled",
    }


def test_generation_conflict_fails_closed(tmp_path: Path) -> None:
    store, wf = fabric(tmp_path)
    setup_hierarchy(wf, store)
    wf.bind_workspace("ws-1", "org-1", "project-1", "env-1")

    with pytest.raises(WorkspaceFabricError, match="generation conflict"):
        wf.bind_workspace(
            "ws-1",
            "org-1",
            "project-1",
            "env-1",
            {"x": True},
            expected_generation=99,
        )


def test_hierarchy_ownership_is_enforced(tmp_path: Path) -> None:
    store, wf = fabric(tmp_path)
    setup_hierarchy(wf, store)
    wf.create_organization("org-2", "Other")

    with pytest.raises(WorkspaceFabricError, match="organization"):
        wf.bind_workspace("ws-1", "org-2", "project-1", "env-1")


def test_environment_must_belong_to_project(tmp_path: Path) -> None:
    store, wf = fabric(tmp_path)
    setup_hierarchy(wf, store)
    wf.create_project("project-2", "org-1", "Other")

    with pytest.raises(WorkspaceFabricError, match="environment"):
        wf.create_environment(
            "env-2",
            "project-2",
            "Production",
            EnvironmentKind.PRODUCTION,
        )

    with pytest.raises(WorkspaceFabricError, match="environment"):
        wf.bind_workspace("ws-1", "org-1", "project-1", "env-missing")


def test_archive_and_restore_are_generation_protected(tmp_path: Path) -> None:
    store, wf = fabric(tmp_path)
    setup_hierarchy(wf, store)
    wf.bind_workspace("ws-1", "org-1", "project-1", "env-1")

    archived = wf.archive_workspace("ws-1", expected_generation=1)
    assert archived.state is WorkspaceState.ARCHIVED
    restored = wf.restore_workspace("ws-1", expected_generation=2)
    assert restored.state is WorkspaceState.ACTIVE
    assert restored.generation == 3


def test_export_contains_effective_configuration(tmp_path: Path) -> None:
    store, wf = fabric(tmp_path)
    setup_hierarchy(wf, store)
    wf.bind_workspace("ws-1", "org-1", "project-1", "env-1", {"local": True})

    exported = wf.export_workspace("ws-1")
    assert exported["workspace"]["workspace_id"] == "ws-1"
    assert exported["effective_configuration"]["region"] == "de"
    assert exported["effective_configuration"]["local"] is True
