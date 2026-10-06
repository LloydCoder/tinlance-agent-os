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
    status: str = "active",
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
        risk_level="low",
        autonomy_level="bounded",
        approval_policy="platform",
        data_sensitivity="public",
        delegation_allowed=False,
        max_delegation_depth=0,
        max_fanout=0,
        evidence_required=False,
        evaluation_suite="phase-27",
        evaluation_score=evaluation,
        trust_score=trust,
        cost_microunits=cost,
        latency_ms=latency,
        provenance=("test",),
        artifact_digest="sha256:test",
        signature_ref="",
        sbom_ref="",
        compatibility={},
        status=status,
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


def test_retrieval_requires_complete_capability_and_skill_coverage() -> None:
    results = retrieve_profiles(
        (
            profile("partial-capability", capabilities=("research.search",)),
            profile(
                "partial-skill",
                capabilities=("research.search", "research.synthesis"),
                skills=("search",),
            ),
            profile(
                "complete",
                capabilities=("research.search", "research.synthesis"),
                skills=("search", "synthesis"),
            ),
        ),
        RetrievalRequirement(
            frozenset({"research.search", "research.synthesis"}),
            frozenset({"search", "synthesis"}),
        ),
    )
    assert [item.profile_id for item in results] == ["complete"]


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


def test_retrieval_excludes_inactive_profiles() -> None:
    results = retrieve_profiles(
        (profile("inactive", status="deprecated"), profile("active")),
        RetrievalRequirement(frozenset({"research.search"})),
    )
    assert [item.profile_id for item in results] == ["active"]


def test_retrieval_rejects_invalid_requirements_and_limit() -> None:
    invalid_requirements = (
        RetrievalRequirement(frozenset({"research.search"}), min_evaluation_score=-0.1),
        RetrievalRequirement(frozenset({"research.search"}), min_trust_score=1.1),
        RetrievalRequirement(frozenset({"research.search"}), max_cost_microunits=-1),
        RetrievalRequirement(frozenset({"research.search"}), max_latency_ms=-1),
    )
    for requirement in invalid_requirements:
        try:
            _ = requirement
        except ValueError:
            pass
        else:
            raise AssertionError("expected invalid requirement failure")

    try:
        RetrievalRequirement(frozenset())
    except ValueError as exc:
        assert "capability" in str(exc)
    else:
        raise AssertionError("expected missing capability failure")

    try:
        retrieve_profiles(
            (profile("x"),), RetrievalRequirement(frozenset({"research.search"})), limit=0
        )
    except ValueError as exc:
        assert "limit" in str(exc)
    else:
        raise AssertionError("expected invalid limit failure")
