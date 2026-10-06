from tinlance_agent_os.catalog_candidates import CandidateState, TaxonomyCandidate
from tinlance_agent_os.catalog_expansion_20k import build_20k_expansion_manifest


def inventory(count: int = 20_000) -> tuple[TaxonomyCandidate, ...]:
    return tuple(
        TaxonomyCandidate(
            name=f"Canonical Archetype {index}",
            description=f"Performs a distinct governed archetype capability for expansion {index}.",
            domain=f"domain-{index % 50}",
            capabilities=(f"capability.{index}",),
            skills=(f"skill.{index}",),
            source_refs=(f"source:{index}",),
            state=CandidateState.CANONICAL,
            canonical_id=f"catalog.agent.{index:05d}",
            review_ref=f"review:catalog:{index}",
        )
        for index in range(count)
    )


def test_20k_manifest_accepts_explicit_inventory() -> None:
    manifest = build_20k_expansion_manifest(inventory())
    assert manifest.target_count == 20_000
    assert manifest.canonical_count == 20_000
    assert manifest.domain_count == 50
    assert manifest.provenance_coverage == 1.0
    assert manifest.review_coverage == 1.0
    assert manifest.semantic_uniqueness == 1.0
    assert len(manifest.inventory_digest) == 64


def test_20k_manifest_is_order_independent() -> None:
    records = inventory()
    first = build_20k_expansion_manifest(records)
    second = build_20k_expansion_manifest(reversed(records))
    assert first.inventory_digest == second.inventory_digest


def test_20k_manifest_rejects_subtarget() -> None:
    try:
        build_20k_expansion_manifest(inventory(19_999))
    except ValueError as exc:
        assert "20K" in str(exc)
    else:
        raise AssertionError("sub-target inventory must fail closed")


def test_20k_manifest_rejects_low_domain_diversity() -> None:
    records = tuple(
        TaxonomyCandidate(
            name=f"Canonical Archetype {index}",
            description=f"Performs a distinct governed archetype capability for expansion {index}.",
            domain="single-domain",
            capabilities=(f"capability.{index}",),
            skills=(f"skill.{index}",),
            source_refs=(f"source:{index}",),
            state=CandidateState.CANONICAL,
            canonical_id=f"catalog.agent.{index:05d}",
            review_ref=f"review:catalog:{index}",
        )
        for index in range(20_000)
    )
    try:
        build_20k_expansion_manifest(records)
    except ValueError as exc:
        assert "domains" in str(exc)
    else:
        raise AssertionError("low domain diversity must fail closed")
