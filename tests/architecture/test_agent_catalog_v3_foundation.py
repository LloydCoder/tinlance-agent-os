from tinlance_agent_os.catalog_taxonomy import CanonicalAgentArchetype, TaxonomyStatus


def test_taxonomy_foundation_is_not_authority() -> None:
    source = CanonicalAgentArchetype(
        id="research.knowledge.research-synthesis-agent",
        version="1.0.0",
        name="Research Synthesis Agent",
        description="Synthesizes evidence-backed research inputs.",
        domain_id="research",
        capability_ids=("research.synthesis",),
        skill_ids=("research.evidence-synthesis",),
        inclusion_criteria=("synthesizes supplied evidence",),
        exclusion_criteria=("does not authorize consequential actions",),
        provenance=(
            __import__("tinlance_agent_os.catalog_taxonomy", fromlist=["TaxonomyProvenance"])
            .TaxonomyProvenance("seed-v1", "taxonomy", "seed:420", "forensic-reconciliation"),
        ),
        status=TaxonomyStatus.CANDIDATE,
    )
    assert source.status is TaxonomyStatus.CANDIDATE
    assert "authorize" in source.exclusion_criteria[0]
