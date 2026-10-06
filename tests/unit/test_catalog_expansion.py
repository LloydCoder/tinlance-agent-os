import pytest

from tinlance_agent_os.catalog_domains import build_domain_catalog
from tinlance_agent_os.catalog_expansion import (
    _WORK_PATTERNS,
    build_phase_26_catalog,
    phase_26_count,
)


def test_phase_26_reaches_2k_without_duplicate_identity() -> None:
    catalog = build_phase_26_catalog()
    assert len(catalog) == 2016
    assert phase_26_count() == 2016
    ids = [item.id for item in catalog]
    assert len(ids) == len(set(ids))


def test_phase_26_uses_all_domains_and_work_patterns() -> None:
    catalog = build_phase_26_catalog()
    assert {item.domain_id for item in catalog} == {item.id for item in build_domain_catalog()}
    assert len(_WORK_PATTERNS) == 42
    assert len(catalog) == len(build_domain_catalog()) * len(_WORK_PATTERNS)


def test_phase_26_entries_are_provenanced_and_canonical() -> None:
    sample = build_phase_26_catalog()[0]
    assert sample.status.value == "canonical"
    assert sample.provenance[0].source_id == "agent-catalog-v3-phase-26"
    assert sample.exclusion_criteria


def test_phase_26_does_not_create_authority_from_scale() -> None:
    for entry in build_phase_26_catalog()[::137]:
        text = " ".join(
            (entry.description, *entry.inclusion_criteria, *entry.exclusion_criteria)
        ).casefold()
        assert "authorization" in text
        assert "tool" in text
        assert "provider" in text


def test_phase_26_cardinality_is_stable() -> None:
    assert phase_26_count() == 48 * 42


@pytest.mark.parametrize("pattern_id,description", _WORK_PATTERNS)
def test_work_pattern_has_semantic_description(pattern_id: str, description: str) -> None:
    assert pattern_id.strip()
    assert description.strip()
