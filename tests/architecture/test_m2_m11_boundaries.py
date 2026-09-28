from pathlib import Path

SRC=Path("src/tinlance_agent_os")
def test_no_domain_product_dependencies() -> None:
    forbidden=("tinlance_agent_platform","fdse","fas","tads","threatfade","hezqara")
    for path in SRC.rglob("*.py"):
        text=path.read_text()
        assert not any(f"import {name}" in text.lower() or f"from {name}" in text.lower() for name in forbidden), path
def test_no_os_authority_duplicates() -> None:
    for path in SRC.rglob("*.py"):
        text=path.read_text().lower()
        assert "authorize(" not in text and "evaluate_policy(" not in text
