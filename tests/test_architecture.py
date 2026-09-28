from pathlib import Path

ROOT = Path(__file__).parents[1]
SRC = ROOT / "src" / "tinlance_agent_os"


def test_no_agent_platform_internal_imports() -> None:
    forbidden = ("tinlance_agent_platform.", "from tinlance_agent_platform", "import tinlance_agent_platform")
    for path in SRC.rglob("*.py"):
        text = path.read_text(encoding="utf-8")
        assert not any(token in text for token in forbidden), path
