from dataclasses import replace

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



def test_20k_manifest_rejects_duplicate_tokens_used_to_inflate_semantic_identity() -> None:
    records = list(inventory())
    first = records[0]
    same_domain = records[50]
    records[0] = replace(
        first,
        capabilities=(first.capabilities[0], first.capabilities[0]),
        skills=(first.skills[0], first.skills[0]),
    )
    records[50] = replace(
        same_domain,
        capabilities=first.capabilities,
        skills=first.skills,
    )
    try:
        build_20k_expansion_manifest(records)
    except ValueError as exc:
        assert "semantic uniqueness" in str(exc)
    else:
        raise AssertionError("repeated capability/skill tokens must not inflate canonical count")


def test_inventory_digest_covers_name_and_description() -> None:
    records = list(inventory())
    original = build_20k_expansion_manifest(records)
    records[0] = replace(
        records[0],
        name="Renamed canonical archetype",
        description="A reviewed description change must alter the inventory digest.",
    )
    changed = build_20k_expansion_manifest(records)
    assert original.inventory_digest != changed.inventory_digest


def test_manifest_rejects_unqualified_coverage_and_malformed_digest() -> None:
    manifest = build_20k_expansion_manifest(inventory())
    try:
        replace(manifest, provenance_coverage=0.99)
    except ValueError as exc:
        assert "provenance_coverage" in str(exc)
    else:
        raise AssertionError("manifest must reject incomplete provenance coverage")
    try:
        replace(manifest, inventory_digest="not-a-sha256-digest")
    except ValueError as exc:
        assert "SHA-256" in str(exc)
    else:
        raise AssertionError("manifest must reject malformed inventory digests")


def test_20k_manifest_requires_normalized_release_identifier() -> None:
    try:
        build_20k_expansion_manifest(inventory(), release=" catalog-v3-20k")
    except ValueError as exc:
        assert "normalized" in str(exc)
    else:
        raise AssertionError("release identifiers must be normalized")
