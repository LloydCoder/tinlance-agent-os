from tinlance_agent_os.catalog_candidates import CandidateState, TaxonomyCandidate
from tinlance_agent_os.catalog_forensics import audit_canonical_inventory


def inventory(count: int = 20_000, domains: int = 50) -> tuple[TaxonomyCandidate, ...]:
    return tuple(
        TaxonomyCandidate(
            name=f"Canonical Archetype {index}",
            description=f"Performs a distinct governed archetype capability for forensic audit {index}.",
            domain=f"domain-{index % domains}",
            capabilities=(f"capability.{index}",),
            skills=(f"skill.{index}",),
            source_refs=(f"source:{index}",),
            state=CandidateState.CANONICAL,
            canonical_id=f"catalog.agent.{index:05d}",
            review_ref=f"review:catalog:{index}",
        )
        for index in range(count)
    )


def test_forensic_audit_passes_valid_inventory() -> None:
    report = audit_canonical_inventory(inventory())
    assert report.passed
    assert report.inspected_count == 20_000
    assert report.canonical_count == 20_000
    assert report.domain_count == 50
    assert report.provenance_coverage == 1.0
    assert report.review_coverage == 1.0
    assert report.semantic_uniqueness == 1.0
    assert len(report.audit_digest) == 64


def test_forensic_audit_is_order_independent() -> None:
    records = inventory()
    first = audit_canonical_inventory(records)
    second = audit_canonical_inventory(reversed(records))
    assert first.audit_digest == second.audit_digest


def test_forensic_audit_reports_multiple_failures() -> None:
    records = list(inventory(20_000))
    original = records[-1]
    duplicate = records[-2]
    records[-1] = TaxonomyCandidate(
        name=original.name,
        description=original.description,
        domain=duplicate.domain,
        capabilities=duplicate.capabilities,
        skills=duplicate.skills,
        source_refs=(),
        state=CandidateState.CANONICAL,
        canonical_id=duplicate.canonical_id,
        review_ref="",
    )
    report = audit_canonical_inventory(records)
    assert not report.passed
    assert "duplicate canonical" in " ".join(report.failures)
    assert "semantic archetype" in " ".join(report.failures)
    assert "provenance" in " ".join(report.failures)
    assert "review evidence" in " ".join(report.failures)


def test_forensic_thresholds_fail_closed() -> None:
    try:
        audit_canonical_inventory(inventory(), minimum_count=0)
    except ValueError as exc:
        assert "positive" in str(exc)
    else:
        raise AssertionError("invalid forensic threshold must fail")
