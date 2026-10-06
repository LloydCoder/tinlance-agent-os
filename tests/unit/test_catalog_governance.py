from tinlance_agent_os.catalog_candidates import CandidateState, TaxonomyCandidate
from tinlance_agent_os.catalog_governance import prepare_evolution_release


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
