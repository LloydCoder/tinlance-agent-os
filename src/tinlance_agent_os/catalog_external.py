"""Untrusted external agent metadata normalization for Catalog v3.

External metadata is discovery evidence only. It never grants authority.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from urllib.parse import urlparse


class ExternalDiscoverySource(StrEnum):
    A2A_AGENT_CARD = "a2a-agent-card"
    CURATED_CATALOG = "curated-catalog"
    DIRECT_CONFIG = "direct-config"


@dataclass(frozen=True, slots=True)
class ExternalSkill:
    id: str
    name: str
    description: str
    tags: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.id.strip() or not self.name.strip() or not self.description.strip():
            raise ValueError("external skill identity and description are required")
        if len(set(self.tags)) != len(self.tags):
            raise ValueError("duplicate external skill tags are not permitted")


@dataclass(frozen=True, slots=True)
class ExternalAgentManifest:
    source: ExternalDiscoverySource
    source_ref: str
    name: str
    description: str
    version: str
    endpoint: str
    skills: tuple[ExternalSkill, ...]
    security_schemes: tuple[str, ...] = ()
    signed: bool = False

    def __post_init__(self) -> None:
        if not self.source_ref.strip() or not self.name.strip():
            raise ValueError("external discovery identity is required")
        if not self.description.strip() or not self.version.strip():
            raise ValueError("external discovery metadata is incomplete")
        parsed = urlparse(self.endpoint)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ValueError("external endpoint must be an absolute HTTP(S) URL")
        if not self.skills:
            raise ValueError("external manifests require at least one skill")
        if self.source is ExternalDiscoverySource.A2A_AGENT_CARD and parsed.scheme != "https":
            raise ValueError("A2A production discovery requires HTTPS")


def normalize_a2a_agent_card(
    card: dict[str, object], source_ref: str
) -> ExternalAgentManifest:
    """Normalize an A2A Agent Card without trusting its declarations."""

    required = ("name", "description", "version", "skills", "url")
    if any(not card.get(key) for key in required):
        raise ValueError("A2A Agent Card is missing required discovery fields")

    raw_skills = card["skills"]
    if not isinstance(raw_skills, list):
        raise ValueError("A2A skills must be an array")

    skills: list[ExternalSkill] = []
    for raw in raw_skills:
        if not isinstance(raw, dict):
            raise ValueError("A2A skill must be an object")
        tags = raw.get("tags", [])
        if not isinstance(tags, list) or not all(isinstance(tag, str) for tag in tags):
            raise ValueError("A2A skill tags must be strings")
        skills.append(
            ExternalSkill(
                id=str(raw.get("id", "")),
                name=str(raw.get("name", "")),
                description=str(raw.get("description", "")),
                tags=tuple(tags),
            )
        )

    schemes = card.get("securitySchemes", {})
    security_schemes = tuple(schemes.keys()) if isinstance(schemes, dict) else ()

    return ExternalAgentManifest(
        source=ExternalDiscoverySource.A2A_AGENT_CARD,
        source_ref=source_ref,
        name=str(card["name"]),
        description=str(card["description"]),
        version=str(card["version"]),
        endpoint=str(card["url"]),
        skills=tuple(skills),
        security_schemes=security_schemes,
        signed=bool(card.get("signatures")),
    )
