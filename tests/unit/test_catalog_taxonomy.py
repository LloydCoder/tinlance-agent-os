from dataclasses import replace

import pytest

from tinlance_agent_os.catalog_taxonomy import (
    CanonicalAgentArchetype,
    TaxonomyAlias,
    TaxonomyCompatibility,
    TaxonomyProvenance,
    TaxonomyStatus,
)


def provenance() -> tuple[TaxonomyProvenance, ...]:
    return (TaxonomyProvenance("seed-v1", "taxonomy", "seed:420", "forensic-reconciliation"),)


def archetype(status: TaxonomyStatus = TaxonomyStatus.CANDIDATE) -> CanonicalAgentArchetype:
    return CanonicalAgentArchetype(
        id="cybersecurity.threat-intelligence.apt-correlation-agent",
        version="1.0.0",
        name="APT Campaign Correlation Agent",
        description="Correlates evidence-backed indicators into bounded campaign hypotheses.",
        domain_id="cybersecurity",
        capability_ids=("cybersecurity.threat-intelligence.correlation",),
        skill_ids=("cybersecurity.threat-intelligence.apt-correlation",),
        inclusion_criteria=("must correlate threat indicators",),
        exclusion_criteria=("does not authorize response actions",),
        provenance=provenance(),
        status=status,
        aliases=("APT Correlation Agent",),
    )


def test_candidate_has_stable_semantic_digest() -> None:
    entry = archetype()
    assert len(entry.semantic_digest) == 64
    assert entry.semantic_digest == archetype().semantic_digest


def test_canonical_requires_exclusion_criteria() -> None:
    with pytest.raises(ValueError, match="exclusion"):
        CanonicalAgentArchetype(
            id="a",
            version="1.0.0",
            name="A",
            description="A",
            domain_id="d",
            capability_ids=("d.c",),
            skill_ids=(),
            inclusion_criteria=("does work",),
            exclusion_criteria=(),
            provenance=provenance(),
            status=TaxonomyStatus.CANONICAL,
        )


def test_duplicate_aliases_fail_closed() -> None:
    with pytest.raises(ValueError, match="duplicate aliases"):
        CanonicalAgentArchetype(
            id="a",
            version="1.0.0",
            name="A",
            description="A",
            domain_id="d",
            capability_ids=("d.c",),
            skill_ids=(),
            inclusion_criteria=("does work",),
            exclusion_criteria=("not authority",),
            provenance=provenance(),
            aliases=("alias", "alias"),
        )


def test_compatibility_relations_are_constrained() -> None:
    TaxonomyCompatibility("seed", "canonical", "equivalent")
    with pytest.raises(ValueError, match="unsupported"):
        TaxonomyCompatibility("seed", "canonical", "authority-grant")


def test_alias_requires_reason() -> None:
    with pytest.raises(ValueError, match="required"):
        TaxonomyAlias("", "canonical", "rename")


def test_semantic_digest_ignores_display_name_and_description() -> None:
    original = archetype()
    renamed = replace(
        original,
        name="A different display name",
        description="Display copy can change without changing semantic identity.",
    )
    assert original.semantic_key == renamed.semantic_key
    assert original.semantic_digest == renamed.semantic_digest


def test_canonical_archetype_rejects_duplicate_normalized_capabilities_and_skills() -> None:
    original = archetype()
    with pytest.raises(ValueError, match="duplicate capability"):
        replace(
            original,
            capability_ids=(
                original.capability_ids[0],
                f"  {original.capability_ids[0].upper()}  ",
            ),
        )
    with pytest.raises(ValueError, match="duplicate skill"):
        replace(
            original,
            skill_ids=(
                original.skill_ids[0],
                f"  {original.skill_ids[0].upper()}  ",
            ),
        )
