from tempfile import TemporaryDirectory
from pathlib import Path

from tinlance_agent_os.catalog_schema import CapabilityProfile
from tinlance_agent_os.catalog_store import CatalogStore, SqliteCatalogStore


def profile(i: str, **kw: object) -> CapabilityProfile:
    return CapabilityProfile(
        id=i,
        version="1",
        domain="security",
        capability_ids=("security.review",),
        provenance=("test",),
        **kw,
    )


def test_catalog_store_indexes_and_replaces_profiles() -> None:
    store = CatalogStore()
    store.upsert(profile("a", tools=("github",), environments=("cloud",)))
    store.upsert(profile("b", tools=("github",), environments=("local",)))
    assert store.ids_for_capability("security.review") == ("a", "b")
    assert [p.id for p in store.search(tools=("github",), environments=("cloud",))] == ["a"]
    store.upsert(profile("a", tools=("slack",), environments=("local",)))
    assert [p.id for p in store.search(tools=("github",))] == ["b"]


def test_sqlite_catalog_store_survives_reopen() -> None:
    with TemporaryDirectory() as directory:
        path = str(Path(directory) / "catalog.db")
        first = SqliteCatalogStore(path)
        first.upsert(
            profile(
                "durable",
                evaluation_score=0.9,
                trust_score=0.95,
                artifact_digest="sha256:abc",
            )
        )
        reopened = SqliteCatalogStore(path)
        loaded = reopened.get("durable")
        assert loaded is not None
        assert loaded.artifact_digest == "sha256:abc"
        assert loaded.trust_score == 0.95
