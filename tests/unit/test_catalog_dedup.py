import pytest

from tinlance_agent_os.catalog_dedup import (
    DeduplicationMatch,
    SemanticDeduplicator,
    SemanticRelation,
    normalize_name,
)
from tinlance_agent_os.catalog_taxonomy import (
    CanonicalAgentArchetype,
    TaxonomyProvenance,
)


def archetype(
    identifier: str,
    name: str,
    *,
    capabilities: tuple[str, ...] = ("research.synthesis",),
    skills: tuple[str, ...] = ("research.synthesis",),
    domain: str = "research",
) -> CanonicalAgentArchetype:
    return CanonicalAgentArchetype(
        id=identifier,
        version="1.0.0",
        name=name,
        description=f"Bounded {name.lower()} capability.",
        domain_id=domain,
        capability_ids=capabilities,
        skill_ids=skills,
        inclusion_criteria=("performs the declared capability",),
        exclusion_criteria=("does not grant authority",),
        provenance=(
            TaxonomyProvenance(
                "phase-24-test",
                "test",
                f"test:{identifier}",
                "deterministic-fixture",
            ),
        ),
    )


def test_normalize_name_is_deterministic() -> None:
    assert normalize_name("  Threat-Intel / Correlation Agent ") == "threat intel correlation agent"


def test_exact_duplicate_is_automatic_equivalence() -> None:
    left = archetype("research.a", "Research Synthesis Agent")
    right = archetype("research.b", "Research Synthesis Agent")
    match = SemanticDeduplicator.compare(left, right)
    assert match.relation is SemanticRelation.EQUIVALENT
    assert match.score == 1.0
    assert match.automatic is True


def test_same_scope_different_name_requires_review() -> None:
    left = archetype("research.a", "Research Synthesis Agent")
    right = archetype("research.b", "Evidence Synthesis Agent")
    match = SemanticDeduplicator.compare(left, right)
    assert match.relation is SemanticRelation.REVIEW_REQUIRED
    assert match.automatic is False


def test_subset_scope_is_specialized() -> None:
    left = archetype("research.a", "Research Agent", skills=("research",))
    right = archetype(
        "research.b",
        "Research And Synthesis Agent",
        capabilities=("research.synthesis", "research.search"),
        skills=("research", "search"),
    )
    match = SemanticDeduplicator.compare(left, right)
    assert match.relation is SemanticRelation.SPECIALIZED
    assert match.automatic is True


def test_superset_scope_is_generalized() -> None:
    left = archetype(
        "research.a",
        "Research And Synthesis Agent",
        capabilities=("research.synthesis", "research.search"),
        skills=("research", "search"),
    )
    right = archetype("research.b", "Research Agent", skills=("research",))
    match = SemanticDeduplicator.compare(left, right)
    assert match.relation is SemanticRelation.GENERALIZED
    assert match.automatic is True


def test_cross_domain_never_auto_merges() -> None:
    left = archetype("research.a", "Research Agent")
    right = archetype("health.a", "Research Agent", domain="healthcare")
    match = SemanticDeduplicator.compare(left, right)
    assert match.relation is SemanticRelation.RELATED_BUT_DISTINCT
    assert match.automatic is False


def test_high_lexical_similarity_with_different_scope_requires_review() -> None:
    left = archetype("research.a", "Threat Intelligence Agent")
    right = archetype(
        "research.b",
        "Threat Intelligence Agent",
        capabilities=("research.search",),
        skills=("research.search",),
    )
    match = SemanticDeduplicator.compare(left, right)
    assert match.relation is SemanticRelation.REVIEW_REQUIRED
    assert match.automatic is False


def test_materially_different_scope_is_distinct() -> None:
    left = archetype("research.a", "Research Agent")
    right = archetype(
        "research.b",
        "Procurement Agent",
        capabilities=("procurement.sourcing",),
        skills=("procurement.sourcing",),
    )
    match = SemanticDeduplicator.compare(left, right)
    assert match.relation is SemanticRelation.RELATED_BUT_DISTINCT
    assert match.automatic is False


def test_report_compares_each_pair_once() -> None:
    entries = (
        archetype("research.a", "Research Agent"),
        archetype("research.b", "Research Agent"),
        archetype("research.c", "Procurement Agent", capabilities=("procurement.sourcing",), skills=("procurement.sourcing",)),
    )
    report = SemanticDeduplicator.report(entries)
    assert report.compared == 3
    assert len(report.matches) == 3


def test_match_rejects_self_comparison_and_bad_score() -> None:
    with pytest.raises(ValueError, match="itself"):
        DeduplicationMatch("a", "a", SemanticRelation.EQUIVALENT, 1.0, "x", True)
    with pytest.raises(ValueError, match="between"):
        DeduplicationMatch("a", "b", SemanticRelation.EQUIVALENT, 1.1, "x", True)


def test_review_required_cannot_be_automatic() -> None:
    with pytest.raises(ValueError, match="automatic"):
        DeduplicationMatch(
            "a",
            "b",
            SemanticRelation.REVIEW_REQUIRED,
            0.9,
            "manual review required",
            True,
        )
