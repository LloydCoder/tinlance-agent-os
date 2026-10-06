from pathlib import Path


def test_catalog_dedup_has_no_authority_dependencies() -> None:
    source = Path("src/tinlance_agent_os/catalog_dedup.py").read_text(encoding="utf-8")
    forbidden = (
        "authorization",
        "approvals.decide",
        "tools.execute",
        "sandbox",
        "secrets",
        "platform_r10",
        "m26_directory",
        "m36_registry",
    )
    lowered = source.casefold()
    assert not any(token.casefold() in lowered for token in forbidden)


def test_catalog_dedup_is_review_safe() -> None:
    source = Path("src/tinlance_agent_os/catalog_dedup.py").read_text(encoding="utf-8")
    assert "REVIEW_REQUIRED" in source
    assert "automatic" in source
