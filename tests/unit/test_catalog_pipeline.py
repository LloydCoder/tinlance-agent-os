import pytest

from tinlance_agent_os.catalog_pipeline import CandidatePipeline
from tinlance_agent_os.catalog_taxonomy import (
    CanonicalAgentArchetype,
    TaxonomyProvenance,
    TaxonomyStatus,
)


def candidate(status: TaxonomyStatus) -> CanonicalAgentArchetype:
    return CanonicalAgentArchetype(
        id="cybersecurity.threat-intelligence.apt-correlation-agent",
        version="1.0.0",
        name="APT Campaign Correlation Agent",
        description="Correlates evidence-backed indicators into bounded hypotheses.",
        domain_id="cybersecurity",
        capability_ids=("cybersecurity.threat-intelligence.correlation",),
        skill_ids=("cybersecurity.threat-intelligence.apt-correlation",),
        inclusion_criteria=("must correlate threat indicators",),
        exclusion_criteria=("does not authorize response actions",),
        provenance=(
            TaxonomyProvenance(
                "seed-v1",
                "taxonomy",
                "seed:420",
                "forensic-reconciliation",
            ),
        ),
        status=status,
    )


def test_pipeline_advances_one_controlled_state() -> None:
    updated, event = CandidatePipeline.transition(
        candidate(TaxonomyStatus.CANDIDATE),
        TaxonomyStatus.VALIDATED,
        "validation passed",
    )
    assert updated.status is TaxonomyStatus.VALIDATED
    assert event.from_status is TaxonomyStatus.CANDIDATE


def test_pipeline_rejects_skipped_review() -> None:
    with pytest.raises(ValueError, match="invalid"):
        CandidatePipeline.transition(
            candidate(TaxonomyStatus.CANDIDATE),
            TaxonomyStatus.CANONICAL,
            "publish directly",
        )


def test_pipeline_rejects_reverse_transition() -> None:
    with pytest.raises(ValueError, match="invalid"):
        CandidatePipeline.transition(
            candidate(TaxonomyStatus.VALIDATED),
            TaxonomyStatus.CANDIDATE,
            "rollback",
        )
