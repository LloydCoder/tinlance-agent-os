"""Deterministic evaluation-aware Catalog retrieval.

Retrieval ranks descriptive capability profiles only. It never admits an
agent, grants authority, or overrides Platform policy.
"""

from __future__ import annotations

from dataclasses import dataclass

from .catalog_schema import CapabilityProfile


@dataclass(frozen=True, slots=True)
class RetrievalRequirement:
    capabilities: frozenset[str]
    skills: frozenset[str] = frozenset()
    domain: str | None = None
    min_evaluation_score: float = 0.0
    min_trust_score: float = 0.0
    max_cost_microunits: int | None = None
    max_latency_ms: int | None = None

    def __post_init__(self) -> None:
        if not self.capabilities:
            raise ValueError("at least one capability is required")
        if not 0.0 <= self.min_evaluation_score <= 1.0:
            raise ValueError("min_evaluation_score must be between 0 and 1")
        if not 0.0 <= self.min_trust_score <= 1.0:
            raise ValueError("min_trust_score must be between 0 and 1")
        if self.max_cost_microunits is not None and self.max_cost_microunits < 0:
            raise ValueError("max_cost_microunits cannot be negative")
        if self.max_latency_ms is not None and self.max_latency_ms < 0:
            raise ValueError("max_latency_ms cannot be negative")


@dataclass(frozen=True, slots=True)
class RetrievalResult:
    profile_id: str
    score: float
    capability_coverage: float
    skill_coverage: float
    rationale: tuple[str, ...]


def retrieve_profiles(
    profiles: tuple[CapabilityProfile, ...],
    requirement: RetrievalRequirement,
    *,
    limit: int = 10,
) -> tuple[RetrievalResult, ...]:
    if limit < 1:
        raise ValueError("retrieval limit must be positive")

    results: list[RetrievalResult] = []
    for profile in profiles:
        if profile.status != "active":
            continue

        profile_capabilities = frozenset(profile.capability_ids)
        profile_skills = frozenset(profile.skill_ids)
        capability_coverage = len(requirement.capabilities & profile_capabilities) / len(
            requirement.capabilities
        )
        skill_coverage = (
            len(requirement.skills & profile_skills) / len(requirement.skills)
            if requirement.skills
            else 1.0
        )

        if requirement.domain and profile.domain != requirement.domain:
            continue
        if capability_coverage < 1.0:
            continue
        if requirement.skills and skill_coverage < 1.0:
            continue
        if profile.evaluation_score < requirement.min_evaluation_score:
            continue
        if profile.trust_score < requirement.min_trust_score:
            continue
        if (
            requirement.max_cost_microunits is not None
            and profile.cost_microunits > requirement.max_cost_microunits
        ):
            continue
        if (
            requirement.max_latency_ms is not None
            and profile.latency_ms > requirement.max_latency_ms
        ):
            continue

        score = round(
            capability_coverage * 0.50
            + skill_coverage * 0.20
            + profile.evaluation_score * 0.15
            + profile.trust_score * 0.15,
            6,
        )
        results.append(
            RetrievalResult(
                profile_id=profile.id,
                score=score,
                capability_coverage=round(capability_coverage, 6),
                skill_coverage=round(skill_coverage, 6),
                rationale=(
                    "all required capabilities and skills matched",
                    "evaluation and trust thresholds applied",
                    "Platform admission remains authoritative",
                ),
            )
        )

    results.sort(key=lambda item: (-item.score, item.profile_id))
    return tuple(results[:limit])
