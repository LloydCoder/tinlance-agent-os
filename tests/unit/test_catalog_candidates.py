from tinlance_agent_os.catalog_candidates import (
    CandidateState,
    TaxonomyCandidate,
    cluster_candidate,
    deduplicate,
    deprecate,
    mark_candidate,
    promote_for_review,
    publish_canonical,
    validate_candidates,
)


def candidate(
    name: str = "Threat Intelligence Analyst",
    *,
    sources: tuple[str, ...] = ("nist:tool-taxonomy",),
    description: str = "Analyzes threat intelligence evidence and produces structured findings.",
) -> TaxonomyCandidate:
    return TaxonomyCandidate(
        name=name,
        description=description,
        domain="Cybersecurity",
        capabilities=("Threat Intelligence Analysis",),
        skills=("Indicator Correlation",),
        source_refs=sources,
    )


def reviewed_candidate() -> TaxonomyCandidate:
    normalized = candidate().normalized()
    clustered = cluster_candidate(normalized)
    marked = mark_candidate(clustered)
    validated = validate_candidates((marked,))[0]
    return promote_for_review(validated, review_ref="review:example")


def test_candidate_requires_provenance() -> None:
    for sources in ((), ("",), ("  ",), ("a", "")):
        try:
            candidate(sources=sources)
        except ValueError as exc:
            assert "provenance" in str(exc)
        else:
            raise AssertionError("blank provenance must fail")


def test_candidate_rejects_blank_capability_or_skill() -> None:
    try:
        TaxonomyCandidate(
            name="Valid Agent",
            description="A sufficiently descriptive candidate for testing.",
            domain="test",
            capabilities=(" ",),
            source_refs=("test",),
        )
    except ValueError as exc:
        assert "capabilities" in str(exc)
    else:
        raise AssertionError("blank capability must fail")

    try:
        TaxonomyCandidate(
            name="Valid Agent",
            description="A sufficiently descriptive candidate for testing.",
            domain="test",
            capabilities=("test.capability",),
            skills=(" ",),
            source_refs=("test",),
        )
    except ValueError as exc:
        assert "skills" in str(exc)
    else:
        raise AssertionError("blank skill must fail")


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


def test_full_lifecycle_requires_each_gate() -> None:
    reviewed = reviewed_candidate()
    canonical = publish_canonical(reviewed, "cybersecurity.threat_intelligence.analyst")
    deprecated = deprecate(canonical)

    assert reviewed.state is CandidateState.REVIEWED
    assert reviewed.review_ref == "review:example"
    assert canonical.state is CandidateState.CANONICAL
    assert canonical.canonical_id == "cybersecurity.threat_intelligence.analyst"
    assert deprecated.state is CandidateState.DEPRECATED
    assert deprecated.canonical_id == canonical.canonical_id
    assert deprecated.review_ref == reviewed.review_ref


def test_cannot_skip_lifecycle_gates() -> None:
    invalid = (
        (candidate(), CandidateState.CANONICAL),
        (candidate(), CandidateState.CLUSTERED),
    )
    for record, target in invalid:
        try:
            record.transition(target, canonical_id="test.id", review_ref="review:example")
        except ValueError:
            pass
        else:
            raise AssertionError("invalid lifecycle transition must fail")

    try:
        promote_for_review(candidate(), review_ref="review:example")
    except ValueError as exc:
        assert "invalid candidate transition" in str(exc)
    else:
        raise AssertionError("unvalidated candidate must not enter review")

    reviewed = reviewed_candidate()
    for invalid_id in ("", "Threat.Intelligence", "bad id"):
        try:
            publish_canonical(reviewed, invalid_id)
        except ValueError as exc:
            assert "canonical" in str(exc)
        else:
            raise AssertionError("invalid canonical ID must fail")


def test_review_attestation_is_required() -> None:
    normalized = candidate().normalized()
    clustered = cluster_candidate(normalized)
    marked = mark_candidate(clustered)
    validated = validate_candidates((marked,))[0]
    try:
        promote_for_review(validated, review_ref="")
    except ValueError as exc:
        assert "review_ref" in str(exc)
    else:
        raise AssertionError("review without evidence reference must fail")


def test_non_discovered_state_cannot_be_fabricated() -> None:
    try:
        TaxonomyCandidate(
            name="Threat Intelligence Analyst",
            description="Analyzes threat intelligence evidence and produces structured findings.",
            domain="Cybersecurity",
            capabilities=("Threat Intelligence Analysis",),
            source_refs=("test",),
            state=CandidateState.CANONICAL,
            canonical_id="cybersecurity.threat_intelligence.analyst",
            review_ref="review:example",
        )
    except ValueError as exc:
        assert "explicit lifecycle transition" in str(exc)
    else:
        raise AssertionError("non-discovered state must not be directly constructible")


def test_canonical_requires_stable_id() -> None:
    reviewed = reviewed_candidate()
    try:
        publish_canonical(reviewed, "")
    except ValueError as exc:
        assert "canonical_id" in str(exc)
    else:
        raise AssertionError("canonical publication without stable id must fail")


def test_validation_rejects_weak_semantics() -> None:
    weak = TaxonomyCandidate(
        name="AI",
        description="too short",
        domain="test",
        capabilities=("test.capability",),
        source_refs=("test",),
    )
    weak_candidate = mark_candidate(cluster_candidate(weak.normalized()))
    try:
        validate_candidates((weak_candidate,))
    except ValueError as exc:
        assert "short" in str(exc)
    else:
        raise AssertionError("weak candidate must fail")
