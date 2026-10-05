"""Reproducible capability matching; no authorization decisions."""

from __future__ import annotations

from dataclasses import dataclass

from .catalog_schema import CapabilityProfile


@dataclass(frozen=True, slots=True)
class MatchRequirement:
    capabilities: frozenset[str]
    domain: str | None = None
    tools: frozenset[str] = frozenset()
    environments: frozenset[str] = frozenset()
    protocols: frozenset[str] = frozenset()


@dataclass(frozen=True, slots=True)
class Match:
    profile: CapabilityProfile
    score: float
    reasons: tuple[str, ...]


def match_profile(
    profile: CapabilityProfile,
    requirement: MatchRequirement,
) -> Match | None:
    capabilities = set(profile.capability_ids)
    if (
        not requirement.capabilities.issubset(capabilities)
        or (requirement.domain and profile.domain != requirement.domain)
    ):
        return None

    missing_tools = requirement.tools - set(profile.tools)
    missing_environments = requirement.environments - set(profile.environments)
    missing_protocols = requirement.protocols - set(profile.protocols)
    if missing_tools or missing_environments or missing_protocols:
        return None

    score = (
        len(requirement.capabilities) * 10
        + len(requirement.tools) * 2
        + len(requirement.environments) * 2
        + len(requirement.protocols) * 2
    )
    return Match(
        profile,
        float(score),
        ("capabilities", "domain", "tools", "environments", "protocols"),
    )
