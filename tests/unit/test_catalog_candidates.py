from tinlance_agent_os.catalog_candidates import (
    CandidateState,
    TaxonomyCandidate,
    deduplicate,
    promote_for_review,
    validate_candidates,
)


def candidate(
    name: str = "Threat Intelligence Analyst",
    *,
    sources: tuple[str, ...] = ("nist:tool-taxonomy",),
    state: CandidateState = CandidateState.DISCOVERED,
    description: str = "Analyzes threat intelligence evidence and produces structured findings.",
) -> TaxonomyCandidate:
    return TaxonomyCandidate(
        name=name,
        description=description,
        domain="Cybersecurity",
        capabilities=("Threat Intelligence Analysis",),
        skills=("Indicator Correlation",),
        source_refs=sources,
        state=state,
    )


def test_candidate_requires_provenance() -> None:
    try:
        candidate(sources=())
    except ValueError as exc:
        assert "provenance" in str(exc)
    else:
        raise AssertionError("candidate without provenance must fail")


def test_normalization_is_deterministic() -> None:
    normalized = candidate(
        name="  Threat   Intelligence Analyst ",
        sources=("b", "a", "a"),
    ).normalized()
    assert normalized.name == "threat intelligence analyst"
    assert normalized.source_refs == ("a", "b")
    assert normalized.state is CandidateState.NORMALIZED


def test_deduplicate_keeps_one_semantic_representative() -> None:
    results = deduplicate(
        (
            candidate(name="Threat Intelligence Analyst", sources=("a",)),
            candidate(name=" threat   intelligence analyst ", sources=("a", "b")),
        )
    )
    assert len(results) == 1
    assert results[0].source_refs == ("a", "b")
    assert len(results[0].fingerprint) == 64


def test_validation_is_review_gated() -> None:
    validated = validate_candidates((candidate(),))
    assert validated[0].state is CandidateState.VALIDATED
    reviewed = promote_for_review(validated[0])
    assert reviewed.state is CandidateState.REVIEWED


def test_cannot_skip_validation_or_promote_directly_to_canonical() -> None:
    try:
        promote_for_review(candidate())
    except ValueError as exc:
        assert "validated" in str(exc)
    else:
        raise AssertionError("unvalidated candidate must not enter review")

    try:
        TaxonomyCandidate(
            name="Valid Agent",
            description="A sufficiently descriptive candidate for testing.",
            domain="test",
            capabilities=("test.capability",),
            source_refs=("test",),
            state=CandidateState.CANONICAL,
        )
    except ValueError as exc:
        assert "canonical_id" in str(exc)
    else:
        raise AssertionError("canonical candidate without stable id must fail")


def test_validation_rejects_weak_semantics() -> None:
    try:
        validate_candidates(
            (
                TaxonomyCandidate(
                    name="AI",
                    description="too short",
                    domain="test",
                    capabilities=("test.capability",),
                    source_refs=("test",),
                ),
            )
        )
    except ValueError as exc:
        assert "short" in str(exc)
    else:
        raise AssertionError("weak candidate must fail")
