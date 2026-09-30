from pathlib import Path

ROOT = Path(__file__).parents[2]
SRC = ROOT / "src" / "tinlance_agent_os"


def test_no_domain_imports_from_integrations_or_apps() -> None:
    domain = (SRC / "domain.py").read_text()
    contracts = (SRC / "contracts.py").read_text()
    assert "integrations" not in domain
    assert "apps" not in domain
    assert "tinlance_agent_platform" not in domain
    assert "tinlance_agent_platform" not in contracts


def test_m0_does_not_embed_domain_products() -> None:
    source = "\n".join(path.read_text() for path in SRC.rglob("*.py"))
    forbidden = (
        "import fas",
        "import tads",
        "import fdse",
        "import threatfade",
        "import hezqara",
    )
    assert not any(token in source.lower() for token in forbidden)


def test_model_gateway_has_no_platform_authority_imports() -> None:
    source = (SRC / "model_gateway.py").read_text()
    forbidden = (
        "agent_platform",
        "platform_adapter",
        "contracts",
        "ApprovalRef",
        "CapabilityRef",
        "EvidenceRef",
        "PlatformRunRef",
    )
    assert not any(token in source for token in forbidden)
