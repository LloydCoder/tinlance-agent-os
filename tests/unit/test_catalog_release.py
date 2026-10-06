from tinlance_agent_os.catalog_candidates import CandidateState, TaxonomyCandidate
from tinlance_agent_os.catalog_release import build_10k_release_manifest


def canonical_inventory(count: int) -> tuple[TaxonomyCandidate, ...]:
    return tuple(
        TaxonomyCandidate(
            name=f"Canonical Agent {index}",
            description=(
                f"Performs a distinct governed catalog capability for release validation {index}."
            ),
            domain=f"domain-{index % 30}",
            capabilities=(f"capability.{index}",),
            skills=(f"skill.{index}",),
            source_refs=(f"source:{index}",),
            state=CandidateState.CANONICAL,
            canonical_id=f"agent.catalog.{index:05d}",
            review_ref=f"review:catalog:{index}",
        )
        for index in range(count)
    )


def test_10k_release_manifest_accepts_valid_inventory() -> None:
    manifest = build_10k_release_manifest(canonical_inventory(10_000))
    assert manifest.release == "catalog-v3-10k"
    assert manifest.target_count == 10_000
    assert manifest.canonical_count == 10_000
    assert manifest.domain_count == 30
    assert manifest.provenance_coverage == 1.0
    assert manifest.semantic_uniqueness == 1.0
    assert len(manifest.inventory_digest) == 64


def test_10k_release_fails_closed_below_target() -> None:
    try:
        build_10k_release_manifest(canonical_inventory(9_999))
    except ValueError as exc:
        assert "10000" in str(exc)
    else:
        raise AssertionError("sub-target inventory must not release")


def test_10k_release_rejects_noncanonical_entries() -> None:
    inventory = list(canonical_inventory(10_000))
    inventory[-1] = TaxonomyCandidate(
        name=inventory[-1].name,
        description=inventory[-1].description,
        domain=inventory[-1].domain,
        capabilities=inventory[-1].capabilities,
        skills=inventory[-1].skills,
        source_refs=inventory[-1].source_refs,
        state=CandidateState.REVIEWED,
        review_ref="review:catalog:9999",
    )
    try:
        build_10k_release_manifest(inventory)
    except ValueError as exc:
        assert "canonical" in str(exc)
    else:
        raise AssertionError("reviewed entry must block release")


def test_10k_release_rejects_duplicate_identity_and_semantics() -> None:
    inventory = list(canonical_inventory(10_000))
    inventory[-1] = inventory[-2]
    try:
        build_10k_release_manifest(inventory)
    except ValueError as exc:
        assert "unique canonical" in str(exc)
    else:
        raise AssertionError("duplicate identity must block release")


def test_10k_release_rejects_renamed_semantic_duplicate() -> None:
    inventory = list(canonical_inventory(10_000))
    original = inventory[-1]
    semantic_source = inventory[-2]
    inventory[-1] = TaxonomyCandidate(
        name="Renamed Agent",
        description="A different description must not create a new semantic archetype.",
        domain=semantic_source.domain,
        capabilities=semantic_source.capabilities,
        skills=semantic_source.skills,
        source_refs=original.source_refs,
        state=CandidateState.CANONICAL,
        canonical_id=original.canonical_id,
        review_ref=original.review_ref,
    )
    try:
        build_10k_release_manifest(inventory)
    except ValueError as exc:
        assert "semantic uniqueness" in str(exc)
    else:
        raise AssertionError("renamed semantic duplicate must block release")


def test_10k_release_digest_is_order_independent() -> None:
    inventory = canonical_inventory(10_000)
    first = build_10k_release_manifest(inventory)
    second = build_10k_release_manifest(reversed(inventory))
    assert first.inventory_digest == second.inventory_digest


def test_10k_release_locks_policy_thresholds() -> None:
    inventory = canonical_inventory(10_000)
    for kwargs, expected in (
        ({"target_count": 9_999}, "target"),
        ({"min_domains": 1}, "diversity"),
        ({"release": "   "}, "release identifier"),
    ):
        try:
            build_10k_release_manifest(inventory, **kwargs)
        except ValueError as exc:
            assert expected in str(exc)
        else:
            raise AssertionError("release policy weakening must be rejected")


def test_10k_release_requires_domain_diversity() -> None:
    inventory = tuple(
        TaxonomyCandidate(
            name=f"Canonical Agent {index}",
            description=(
                f"Performs a distinct governed catalog capability for release validation {index}."
            ),
            domain="single-domain",
            capabilities=(f"capability.{index}",),
            skills=(f"skill.{index}",),
            source_refs=(f"source:{index}",),
            state=CandidateState.CANONICAL,
            canonical_id=f"agent.catalog.{index:05d}",
            review_ref=f"review:catalog:{index}",
        )
        for index in range(10_000)
    )
    try:
        build_10k_release_manifest(inventory)
    except ValueError as exc:
        assert "domains" in str(exc)
    else:
        raise AssertionError("low domain diversity must block release")
