from pathlib import Path


def test_domain_catalog_does_not_become_an_authority_plane() -> None:
    source = Path("src/tinlance_agent_os/catalog_domains.py").read_text(encoding="utf-8").casefold()
    forbidden = (
        "tools.execute",
        "approvals.decide",
        "sandbox",
        "secrets",
        "platform_r10",
        "m26_directory",
        "m36_registry",
    )
    assert not any(token in source for token in forbidden)


def test_domain_catalog_has_explicit_non_inflation_boundary() -> None:
    source = Path("src/tinlance_agent_os/catalog_domains.py").read_text(encoding="utf-8")
    assert "geography" in source
    assert "authorization" in source
    assert "customer" in source
