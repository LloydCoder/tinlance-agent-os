import pytest

from tinlance_agent_os.catalog_pipeline import CandidatePipeline
from tinlance_agent_os.catalog_taxonomy import CanonicalAgentArchetype, TaxonomyProvenance, TaxonomyStatus

def candidate(status: TaxonomyStatus) -> CanonicalAgentArchetype:
    return CanonicalAgentArchetype(
        id="research.knowledge.synthesis-agent", version="1.0.0",
        name="Research Synthesis Agent", description="Synthesizes supplied evidence.",
        domain_id="research", capability_ids=("research.synthesis",), skill_ids=(),
        inclusion_criteria=("synthesizes supplied evidence",),
        exclusion_criteria=("does not authorize consequential actions",),
        provenance=(TaxonomyProvenance("seed-v1", "taxonomy", "seed:420", "forensic"),),
        status=status,
    )

def test_pipeline_advances_one_controlled_state() -> None:
    updated, event = CandidatePipeline.transition(candidate(TaxonomyStatus.CANDIDATE), TaxonomyStatus.VALIDATED, "validation passed")
    assert updated.status is TaxonomyStatus.VALIDATED
    assert event.from_status is TaxonomyStatus.CANDIDATE

def test_pipeline_rejects_skipped_review() -> None:
    with pytest.raises(ValueError, match="invalid"):
        CandidatePipeline.transition(candidate(TaxonomyStatus.CANDIDATE), TaxonomyStatus.CANONICAL, "publish directly")

def test_pipeline_rejects_reverse_transition() -> None:
    with pytest.raises(ValueError, match="invalid"):
        CandidatePipeline.transition(candidate(TaxonomyStatus.VALIDATED), TaxonomyStatus.CANDIDATE, "rollback")
