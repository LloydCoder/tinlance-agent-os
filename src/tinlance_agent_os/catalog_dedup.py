"""Deterministic semantic deduplication for Agent Catalog v3.

This module reconciles candidate archetypes without making probabilistic
matching an authority. Exact semantic equivalence may be classified
automatically; ambiguous similarity is surfaced for human review.
"""

from __future__ import annotations

from dataclasses import dataclass
from difflib import SequenceMatcher
import re
from enum import StrEnum

from .catalog_taxonomy import CanonicalAgentArchetype


class SemanticRelation(StrEnum):
    EQUIVALENT = "equivalent"
    SPECIALIZED = "specialized"
    GENERALIZED = "generalized"
    RELATED_BUT_DISTINCT = "related-but-distinct"
    REVIEW_REQUIRED = "review-required"


@dataclass(frozen=True, slots=True)
class DeduplicationMatch:
    left_id: str
    right_id: str
    relation: SemanticRelation
    score: float
    reason: str
    automatic: bool

    def __post_init__(self) -> None:
        if not self.left_id.strip() or not self.right_id.strip():
            raise ValueError("deduplication match identities are required")
        if self.left_id == self.right_id:
            raise ValueError("deduplication cannot compare an archetype with itself")
        if not 0.0 <= self.score <= 1.0:
            raise ValueError("deduplication score must be between 0 and 1")
        if not self.reason.strip():
            raise ValueError("deduplication match reason is required")
        if self.automatic and self.relation is SemanticRelation.REVIEW_REQUIRED:
            raise ValueError("review-required matches cannot be automatic")


@dataclass(frozen=True, slots=True)
class DeduplicationReport:
    matches: tuple[DeduplicationMatch, ...]
    compared: int

    def __post_init__(self) -> None:
        if self.compared < 0:
            raise ValueError("compared count cannot be negative")


_TOKEN_RE = re.compile(r"[a-z0-9]+")


def normalize_name(value: str) -> str:
    """Normalize a display name for deterministic comparison only."""
    return " ".join(_TOKEN_RE.findall(value.casefold()))


def _token_set(value: str) -> frozenset[str]:
    return frozenset(_TOKEN_RE.findall(value.casefold()))


def _set_overlap(left: frozenset[str], right: frozenset[str]) -> float:
    if not left and not right:
        return 1.0
    if not left or not right:
        return 0.0
    return len(left & right) / len(left | right)


def _lexical_score(left: CanonicalAgentArchetype, right: CanonicalAgentArchetype) -> float:
    normalized_left = normalize_name(left.name)
    normalized_right = normalize_name(right.name)
    sequence = SequenceMatcher(None, normalized_left, normalized_right).ratio()
    tokens = _set_overlap(_token_set(left.name), _token_set(right.name))
    return round((sequence + tokens) / 2, 6)


def _semantic_relation(
    left: CanonicalAgentArchetype,
    right: CanonicalAgentArchetype,
) -> tuple[SemanticRelation, float, str, bool]:
    if left.semantic_digest == right.semantic_digest:
        return (
            SemanticRelation.EQUIVALENT,
            1.0,
            "identical deterministic semantic digest",
            True,
        )

    if left.domain_id != right.domain_id:
        return (
            SemanticRelation.RELATED_BUT_DISTINCT,
            _lexical_score(left, right),
            "different domains prevent automatic semantic merging",
            False,
        )

    left_caps = frozenset(left.capability_ids)
    right_caps = frozenset(right.capability_ids)
    left_skills = frozenset(left.skill_ids)
    right_skills = frozenset(right.skill_ids)

    if left_caps == right_caps and left_skills == right_skills:
        if normalize_name(left.name) == normalize_name(right.name):
            return (
                SemanticRelation.EQUIVALENT,
                1.0,
                "same domain, capabilities, skills and normalized name",
                True,
            )
        return (
            SemanticRelation.REVIEW_REQUIRED,
            _lexical_score(left, right),
            "same semantic capability/skill boundary but different names require review",
            False,
        )

    if left_caps <= right_caps and left_skills <= right_skills:
        return (
            SemanticRelation.SPECIALIZED,
            0.9,
            "left semantic scope is a subset of right semantic scope",
            True,
        )

    if right_caps <= left_caps and right_skills <= left_skills:
        return (
            SemanticRelation.GENERALIZED,
            0.9,
            "right semantic scope is a subset of left semantic scope",
            True,
        )

    score = _lexical_score(left, right)
    if score >= 0.88:
        return (
            SemanticRelation.REVIEW_REQUIRED,
            score,
            "high lexical similarity with non-equivalent semantic scope",
            False,
        )

    return (
        SemanticRelation.RELATED_BUT_DISTINCT,
        score,
        "semantic boundaries are materially different",
        False,
    )


class SemanticDeduplicator:
    """Compare archetypes without silently merging ambiguous candidates."""

    @staticmethod
    def compare(
        left: CanonicalAgentArchetype,
        right: CanonicalAgentArchetype,
    ) -> DeduplicationMatch:
        relation, score, reason, automatic = _semantic_relation(left, right)
        return DeduplicationMatch(
            left_id=left.id,
            right_id=right.id,
            relation=relation,
            score=score,
            reason=reason,
            automatic=automatic,
        )

    @classmethod
    def report(
        cls,
        archetypes: tuple[CanonicalAgentArchetype, ...],
    ) -> DeduplicationReport:
        matches: list[DeduplicationMatch] = []
        for index, left in enumerate(archetypes):
            for right in archetypes[index + 1 :]:
                matches.append(cls.compare(left, right))
        return DeduplicationReport(tuple(matches), len(matches))
