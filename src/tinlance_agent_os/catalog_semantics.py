"""Canonical semantic identity helpers shared by catalog ingestion and taxonomy.

Identity is based on the normalized domain/capability/skill set, never display
labels. Structured encoding avoids delimiter collisions; duplicate tokens do
not create additional archetypes.
"""

from __future__ import annotations

import json
import unicodedata


def normalize_semantic_token(value: str) -> str:
    """Normalize a taxonomy token using Unicode compatibility normalization."""
    return " ".join(unicodedata.normalize("NFKC", value).split()).casefold()


def canonical_semantic_key(
    domain: str,
    capabilities: tuple[str, ...],
    skills: tuple[str, ...],
) -> str:
    """Return collision-safe identity independent of display metadata."""
    payload = {
        "domain": normalize_semantic_token(domain),
        "capabilities": sorted({normalize_semantic_token(value) for value in capabilities}),
        "skills": sorted({normalize_semantic_token(value) for value in skills}),
    }
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
