"""Deterministic agent selection over matched Catalog candidates."""

from __future__ import annotations

from dataclasses import dataclass

from .catalog_matcher import Match


@dataclass(frozen=True, slots=True)
class Selection:
    profile_id: str
    score: float
    rationale: tuple[str, ...]


def select(matches: tuple[Match, ...]) -> Selection | None:
    if not matches:
        return None
    winner = min(matches, key=lambda match: (-match.score, match.profile.id))
    return Selection(
        winner.profile.id,
        winner.score,
        (
            "highest deterministic fit",
            "catalog-only; Platform admission required",
        ),
    )
