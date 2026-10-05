import json
from pathlib import Path

ROOT = Path(__file__).parents[2]
CATALOG = ROOT / "docs" / "agent-catalog-v2"


def test_phase1_gap_matrix_is_machine_readable() -> None:
    payload = json.loads((CATALOG / "phase-1-gap-matrix.json").read_text())
    assert payload["phase"] == "1"
    assert payload["status"] == "implemented-audit"
    assert "canonical_ontology" in payload["missing"]
    assert "authorization" in payload["forbidden_duplicates"]


def test_phase1_forensic_audit_freezes_existing_authority_owners() -> None:
    text = (CATALOG / "PHASE-1-FORENSIC-AUDIT.md").read_text()
    for owner in ("M17", "M26", "M36", "R10", "Platform"):
        assert owner in text
    assert "No new repository is justified." in text
    assert "No Platform authority contract must be moved" in text
