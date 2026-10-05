import json
from pathlib import Path

ROOT = Path(__file__).parents[2]
CATALOG = ROOT / "docs" / "agent-catalog-v2"


def test_taxonomy_reconciliation_covers_all_seed_entries() -> None:
    payload = json.loads((CATALOG / "taxonomy-v1-reconciled.json").read_text())
    assert payload["seed_entries"] == 420
    assert payload["categories"] == 30
    assert payload["unresolved"] == 0
    assert len(payload["category_counts"]) == 30
    assert sum(payload["category_counts"].values()) == 420


def test_taxonomy_reconciliation_forbids_duplicate_authority_planes() -> None:
    payload = json.loads((CATALOG / "taxonomy-v1-reconciled.json").read_text())
    assert "authorization" in payload["forbidden_reimplementation"]
    assert "m17_coordination" in payload["forbidden_reimplementation"]
    assert "m26_directory" in payload["forbidden_reimplementation"]
    assert "m36_registry" in payload["forbidden_reimplementation"]
    assert "platform_r10" in payload["forbidden_reimplementation"]
