from pathlib import Path

ROOT = Path(__file__).parents[2]
DOC = ROOT / "docs" / "agent-catalog-v2" / "PHASE-3-ECOSYSTEM-RESEARCH.md"


def test_phase3_covers_required_ecosystem_surfaces() -> None:
    text = DOC.read_text()
    for term in ("A2A", "MCP", "NIST", "OWASP", "OpenAI Agents SDK", "Microsoft Agent Framework"):
        assert term in text
    assert "Discovery metadata is not authorization." in text
    assert "External metadata source receives implicit authority" not in text
