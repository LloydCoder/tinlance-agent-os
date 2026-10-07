from pathlib import Path

from tinlance_agent_os.catalog_expansion_20k import MIN_DOMAINS, TARGET_COUNT


ROOT = Path(__file__).resolve().parents[2]


def test_20k_is_a_release_milestone_not_a_hard_ceiling() -> None:
    assert TARGET_COUNT == 20_000
    assert MIN_DOMAINS >= 50
    docs = (ROOT / "docs/agent-catalog-v3-FINAL-GA-FORENSIC-AUDIT.md").read_text(encoding="utf-8")
    assert "continuous governed evolution" in docs.lower()
    assert "20k" in docs.lower()


def test_catalog_readme_preserves_historical_420_seed_semantics() -> None:
    docs = (ROOT / "docs/agent-catalog-v2/README.md").read_text(encoding="utf-8")
    assert "historical seed count" in docs
    assert "not a claim that exactly 420 permanent agents" in docs
