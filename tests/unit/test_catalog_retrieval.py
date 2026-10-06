from tinlance_agent_os.catalog_retrieval import RetrievalRequirement, retrieve_profiles
from tinlance_agent_os.catalog_schema import CapabilityProfile


def profile(
    identifier: str,
    *,
    capabilities: tuple[str, ...] = ("research.search",),
    skills: tuple[str, ...] = ("search",),
    evaluation: float = 0.8,
    trust: float = 0.8,
    cost: int = 100,
    latency: int = 100,
) -> CapabilityProfile:
    return CapabilityProfile(
        id=identifier,
        version="1.0.0",
        domain="research",
        capability_ids=capabilities,
        skill_ids=skills,
        inputs=(),
        outputs=(),
        tools=(),
        environments=(),
        modalities=(),
        protocols=(),
        models=(),
        risk="low",
        autonomy="bounded",
        approval_policy="platform",
        data_sensitivity="public",
        delegation_allowed=False,
        max_delegation_depth=0,
        max_fanout=1,
        evidence_required=False,
        evaluation_suite="phase-27",
        evaluation_score=evaluation,
        trust_score=trust,
        cost_microunits=cost,
        latency_ms=latency,
        provenance="test",
        artifact_digest="sha256:test",
        signature_ref=None,
        sbom_ref=None,
        compatibility=(),
        status="active",
    )


def test_retrieval_ranks_deterministically() -> None:
    results = retrieve_profiles(
        (
            profile("b", evaluation=0.9, trust=0.9),
            profile("a", evaluation=0.9, trust=0.9),
            profile(
                "c",
                capabilities=("research.search", "research.synthesis"),
                skills=("search", "synthesis"),
            ),
        ),
        RetrievalRequirement(
            frozenset({"research.search"}),
            frozenset({"search"}),
        ),
    )
    assert [item.profile_id for item in results] == ["a", "b", "c"]
    assert results[0].score == results[1].score


def test_retrieval_applies_hard_thresholds() -> None:
    results = retrieve_profiles(
        (
            profile("low-eval", evaluation=0.7),
            profile("good", evaluation=0.9, trust=0.95),
        ),
        RetrievalRequirement(frozenset({"research.search"}), min_evaluation_score=0.8),
    )
    assert [item.profile_id for item in results] == ["good"]


def test_retrieval_supports_cost_and_latency_limits() -> None:
    results = retrieve_profiles(
        (
            profile("cheap-fast", cost=50, latency=50),
            profile("expensive", cost=500, latency=500),
        ),
        RetrievalRequirement(
            frozenset({"research.search"}),
            max_cost_microunits=100,
            max_latency_ms=100,
        ),
    )
    assert [item.profile_id for item in results] == ["cheap-fast"]


def test_retrieval_rejects_missing_capability_and_invalid_limit() -> None:
    assert not retrieve_profiles(
        (profile("x", capabilities=("other",)),),
        RetrievalRequirement(frozenset({"research.search"})),
    )
    try:
        retrieve_profiles(
            (profile("x"),), RetrievalRequirement(frozenset({"research.search"})), limit=0
        )
    except ValueError as exc:
        assert "limit" in str(exc)
    else:
        raise AssertionError("expected invalid limit failure")
