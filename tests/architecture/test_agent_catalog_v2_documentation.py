from pathlib import Path


ROOT = Path(__file__).parents[2]
CATALOG = ROOT / "docs" / "agent-catalog-v2"


def test_all_catalog_phase_documents_exist() -> None:
    required = {
        0: "ARCHITECTURE.md",
        1: "PHASE-1-FORENSIC-AUDIT.md",
        2: "PHASE-2-TAXONOMY-RECONCILIATION.md",
        3: "PHASE-3-ECOSYSTEM-RESEARCH.md",
        4: "PHASE-4-ONTOLOGY.md",
        5: "PHASE-5-CAPABILITY-SCHEMA.md",
        6: "PHASE-6-CATALOG-STORAGE.md",
        7: "PHASE-7-AGENT-PROFILES.md",
        8: "PHASE-8-DISCOVERY.md",
        9: "PHASE-9-MATCHING.md",
        10: "PHASE-10-SELECTION.md",
        11: "PHASE-11-TEAM-SPEC.md",
        12: "PHASE-12-TEAM-PLANNER.md",
        13: "PHASE-13-TEAM-COMPOSER.md",
        14: "PHASE-14-GOVERNED-EXECUTION.md",
        15: "PHASE-15-HANDOFF-SYNTHESIS.md",
        16: "PHASE-16-INTEROPERABILITY.md",
        17: "PHASE-17-EVALUATION.md",
        18: "PHASE-18-SECURITY-VALIDATION.md",
        19: "PHASE-19-PRODUCTION-HARDENING.md",
        20: "PHASE-20-GA.md",
    }
    assert all((CATALOG / name).is_file() for name in required.values())


def test_catalog_ga_documentation_is_reconciled() -> None:
    readme = (CATALOG / "README.md").read_text()
    assert "| 20 | GA/continuous discovery | COMPLETE |" in readme
    assert "zero unresolved classifications" in readme
