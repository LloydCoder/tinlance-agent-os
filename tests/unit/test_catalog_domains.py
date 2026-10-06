import pytest

from tinlance_agent_os.catalog_domains import (
    CanonicalDomain,
    DomainFamily,
    build_domain_catalog,
)


def test_phase_25_domain_catalog_is_nonempty_and_unique() -> None:
    domains = build_domain_catalog()
    ids = [item.id for item in domains]
    assert len(domains) >= 48
    assert len(ids) == len(set(ids))


def test_domain_records_are_descriptive_only() -> None:
    domain = build_domain_catalog()[0]
    record = domain.to_record()
    assert record["schema"] == "tinlance.agent-domain.v1"
    assert "authorization" in domain.exclusion_criteria[0]


def test_domain_families_are_explicit() -> None:
    domains = build_domain_catalog()
    assert {item.family for item in domains} == set(DomainFamily)


def test_domain_requires_inclusion_and_exclusion_boundaries() -> None:
    with pytest.raises(ValueError, match="criteria"):
        CanonicalDomain(
            id="research.test",
            family=DomainFamily.SCIENCE,
            name="Research",
            description="Research",
            inclusion_criteria=(),
            exclusion_criteria=("not authority",),
        )


def test_domain_ids_are_namespaced() -> None:
    with pytest.raises(ValueError, match="namespaced"):
        CanonicalDomain(
            id="research",
            family=DomainFamily.SCIENCE,
            name="Research",
            description="Research",
            inclusion_criteria=("research",),
            exclusion_criteria=("not authority",),
        )


def test_domain_semantic_key_is_stable() -> None:
    domain = build_domain_catalog()[0]
    assert domain.semantic_key == domain.semantic_key
