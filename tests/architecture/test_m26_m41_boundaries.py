from pathlib import Path


ROOT = Path(__file__).parents[2]
SRC = ROOT / "src" / "tinlance_agent_os"


def test_advanced_runtime_modules_preserve_platform_boundary() -> None:
    for name in (
        "adaptive.py",
        "assurance.py",
        "enterprise_security.py",
        "evaluation.py",
        "fleet.py",
        "operator.py",
        "registry.py",
        "resource.py",
        "reliability.py",
    ):
        source = (SRC / name).read_text()
        assert "platform_adapter" not in source
        assert "AgentPlatformClient" not in source


def test_m40_m41_are_exposed_as_os_intelligence_not_authority() -> None:
    adaptive = (SRC / "adaptive.py").read_text()
    assurance = (SRC / "assurance.py").read_text()
    assert "authorization" not in adaptive.lower()
    assert "grant_capability" not in adaptive.lower()
    assert "authorize" not in assurance.lower()
