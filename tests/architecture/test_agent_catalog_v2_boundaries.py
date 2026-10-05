from pathlib import Path

ROOT = Path(__file__).parents[2]
DOCS = ROOT / "docs" / "agent-catalog-v2"


def test_catalog_v2_phase0_architecture_artifacts_exist() -> None:
    required = (
        "README.md",
        "ARCHITECTURE.md",
        "TERMINOLOGY.md",
        "OWNERSHIP.md",
    )
    assert all((DOCS / name).is_file() for name in required)
    assert (ROOT / "docs" / "adr" / "0005-agent-catalog-v2-architecture.md").is_file()


def test_catalog_v2_freezes_authority_boundary() -> None:
    architecture = (DOCS / "ARCHITECTURE.md").read_text()
    terminology = (DOCS / "TERMINOLOGY.md").read_text()
    ownership = (DOCS / "OWNERSHIP.md").read_text()

    assert "Platform admission" in architecture
    assert "Catalog v2" in architecture
    assert "M26 Directory" in architecture
    assert "M36 Registry" in architecture
    assert "M17" in architecture
    assert "authority" in terminology.lower()
    assert "authoritative" in ownership.lower()


def test_catalog_v2_does_not_create_a_second_authority_plane() -> None:
    source = "\n".join(path.read_text() for path in (ROOT / "src" / "tinlance_agent_os").rglob("*.py"))
    forbidden = (
        "grant_capability(",
        "mint_capability(",
        "authorize_action(",
        "local_authorization_engine",
        "duplicate_platform_authorization",
    )
    assert not any(token in source for token in forbidden)
