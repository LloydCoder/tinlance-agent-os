from dataclasses import replace

from tinlance_agent_os.catalog_candidates import CandidateState, TaxonomyCandidate
from tinlance_agent_os.catalog_forensics import audit_canonical_inventory


def inventory(count: int = 20_000, domains: int = 50) -> tuple[TaxonomyCandidate, ...]:
    return tuple(
        TaxonomyCandidate(
            name=f"Canonical Archetype {index}",
            description=(
                f"Performs a distinct governed archetype capability for forensic audit {index}."
            ),
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
    corrupt = TaxonomyCandidate(
        name=original.name,
        description=original.description,
        domain=duplicate.domain,
        capabilities=duplicate.capabilities,
        skills=duplicate.skills,
        source_refs=("source:corrupt",),
        state=CandidateState.CANONICAL,
        canonical_id=duplicate.canonical_id,
        review_ref="review:corrupt",
    )
    object.__setattr__(corrupt, "source_refs", ())
    object.__setattr__(corrupt, "review_ref", "")
    records[-1] = corrupt
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


def test_forensic_audit_detects_semantic_inflation_from_duplicate_tokens() -> None:
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
    report = audit_canonical_inventory(records)
    assert not report.passed
    assert "semantic archetype duplicates" in " ".join(report.failures)
    assert report.semantic_uniqueness == 0.0


def test_forensic_digest_changes_when_canonical_metadata_changes() -> None:
    records = list(inventory())
    original = audit_canonical_inventory(records)
    records[0] = replace(
        records[0],
        name="Renamed canonical archetype",
        description="A reviewed description change must alter the audit digest.",
    )
    changed = audit_canonical_inventory(records)
    assert original.audit_digest != changed.audit_digest


def test_forensic_digest_is_order_independent_for_invalid_duplicate_ids() -> None:
    records = list(inventory(2, domains=1))
    records[1] = replace(
        records[1],
        canonical_id=records[0].canonical_id,
        name="Conflicting duplicate identity",
    )
    first = audit_canonical_inventory(records, minimum_count=1, minimum_domains=1)
    second = audit_canonical_inventory(reversed(records), minimum_count=1, minimum_domains=1)
    assert not first.passed
    assert first.audit_digest == second.audit_digest
