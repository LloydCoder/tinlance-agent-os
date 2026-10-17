from dataclasses import replace

from tinlance_agent_os.catalog_candidates import CandidateState, TaxonomyCandidate
from tinlance_agent_os.catalog_governance import EvolutionRelease, prepare_evolution_release


def candidate(
    index: int,
    state: CandidateState = CandidateState.CANONICAL,
) -> TaxonomyCandidate:
    return TaxonomyCandidate(
        name=f"Agent {index}",
        description=f"Performs a distinct governed capability for GA evolution {index}.",
        domain=f"domain-{index}",
        capabilities=(f"capability.{index}",),
        skills=(f"skill.{index}",),
        source_refs=(f"source:{index}",),
        state=state,
        canonical_id=f"catalog.agent.{index}",
        review_ref=f"review:{index}",
    )


def test_prepare_evolution_release_is_deterministic() -> None:
    release = prepare_evolution_release(
        base=(candidate(1),),
        proposed=(candidate(1), candidate(2)),
        release_id="catalog-v3-35.1",
        governance_ref="review:ga",
    )
    assert release.added_ids == ("catalog.agent.2",)
    assert release.deprecated_ids == ()
    assert len(release.base_digest) == 64
    assert len(release.inventory_digest) == 64


def test_deprecation_is_explicit_and_history_preserving() -> None:
    release = prepare_evolution_release(
        base=(candidate(1), candidate(2)),
        proposed=(candidate(1), candidate(2, CandidateState.DEPRECATED)),
        release_id="catalog-v3-35.2",
        governance_ref="review:deprecate",
    )
    assert release.added_ids == ()
    assert release.deprecated_ids == ("catalog.agent.2",)


def test_governance_evidence_is_required() -> None:
    try:
        prepare_evolution_release(
            base=(candidate(1),),
            proposed=(candidate(1),),
            release_id="catalog-v3-35.1",
            governance_ref="",
        )
    except ValueError as exc:
        assert "governance" in str(exc)
    else:
        raise AssertionError("release without governance evidence must fail")


def test_evolution_rejects_unreviewed_records() -> None:
    record = candidate(2)
    object.__setattr__(record, "review_ref", "")
    try:
        prepare_evolution_release(
            base=(candidate(1),),
            proposed=(candidate(1), record),
            release_id="catalog-v3-35.1",
            governance_ref="review:ga",
        )
    except ValueError as exc:
        assert "review evidence" in str(exc)
    else:
        raise AssertionError("unreviewed evolved record must fail")


def test_evolution_rejects_duplicate_ids_and_active_semantic_duplicates() -> None:
    first = candidate(1)
    duplicate_id = candidate(2)
    object.__setattr__(duplicate_id, "canonical_id", first.canonical_id)
    try:
        prepare_evolution_release(
            base=(first,),
            proposed=(first, duplicate_id),
            release_id="catalog-v3-35.3",
            governance_ref="review:ga",
        )
    except ValueError as exc:
        assert "duplicate canonical IDs" in str(exc)
    else:
        raise AssertionError("duplicate canonical IDs must block evolution")

    semantic_duplicate = TaxonomyCandidate(
        name="Renamed Agent",
        description="Different display text cannot create a distinct semantic archetype.",
        domain=first.domain,
        capabilities=first.capabilities,
        skills=first.skills,
        source_refs=("source:renamed",),
        state=CandidateState.CANONICAL,
        canonical_id="catalog.agent.renamed",
        review_ref="review:renamed",
    )
    try:
        prepare_evolution_release(
            base=(first,),
            proposed=(first, semantic_duplicate),
            release_id="catalog-v3-35.4",
            governance_ref="review:ga",
        )
    except ValueError as exc:
        assert "semantic duplicates" in str(exc)
    else:
        raise AssertionError("active semantic duplicates must block evolution")


def test_evolution_digest_binds_display_metadata_and_review_evidence() -> None:
    first = candidate(1)
    changed = replace(
        first,
        name="Renamed Agent",
        description="Updated reviewed description.",
        review_ref="review:updated",
    )
    release = prepare_evolution_release(
        base=(first,),
        proposed=(changed,),
        release_id="catalog-v3-35.5",
        governance_ref="review:ga",
    )
    assert release.base_digest != release.inventory_digest


def test_evolution_release_rejects_malformed_digest() -> None:
    try:
        EvolutionRelease(
            release_id="catalog-v3-35.6",
            base_digest="bad",
            inventory_digest="a" * 64,
            added_ids=(),
            deprecated_ids=(),
            governance_ref="review:ga",
        )
    except ValueError as exc:
        assert "base_digest" in str(exc)
    else:
        raise AssertionError("malformed evolution digest must fail closed")


def test_evolution_release_rejects_untrimmed_identity() -> None:
    try:
        EvolutionRelease(
            release_id=" catalog-v3-35.6",
            base_digest="a" * 64,
            inventory_digest="b" * 64,
            added_ids=(),
            deprecated_ids=(),
            governance_ref="review:ga",
        )
    except ValueError as exc:
        assert "release_id" in str(exc)
    else:
        raise AssertionError("untrimmed release identity must fail closed")


def test_evolution_rejects_destructive_deletion_of_historical_ids() -> None:
    try:
        prepare_evolution_release(
            base=(candidate(1), candidate(2)),
            proposed=(candidate(1),),
            release_id="catalog-v3-35.7",
            governance_ref="review:ga",
        )
    except ValueError as exc:
        assert "cannot delete historical IDs" in str(exc)
    else:
        raise AssertionError("historical entries must be explicitly deprecated, not deleted")


def test_evolution_rejects_reactivation_of_deprecated_ids() -> None:
    try:
        prepare_evolution_release(
            base=(candidate(1, CandidateState.DEPRECATED),),
            proposed=(candidate(1, CandidateState.CANONICAL),),
            release_id="catalog-v3-35.8",
            governance_ref="review:ga",
        )
    except ValueError as exc:
        assert "cannot be reactivated" in str(exc)
    else:
        raise AssertionError("deprecated canonical IDs must not be reactivated")
